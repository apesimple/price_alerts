import os
import sys
import pid
import time
import math
from pathlib import Path
from datetime import datetime
from slack_functions import send_slack_msg
from brownie import *

parent_dir = Path(__file__).resolve().parents[1]
p = project.load(parent_dir)

network.connect('mainnet_local')

USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
WBTC = '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
# LUNA = '0xd2877702675e6ceb975b4a1dff9fb7baf4c91ea9'
# CVX = '0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b'
# FXS = '0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0'

SUSHISWAP_ROUTER_ADDRESS = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
SUSHISWAP = p.interface.IUniswapV2Router02(SUSHISWAP_ROUTER_ADDRESS)
# UNISWAP_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
# UNISWAP = p.interface.IUniswapV2Router02(UNISWAP_ROUTER_ADDRESS)

BLOCK_RECORDS = 60   # About 15 min
USDC_AMOUNT = 100

TOKENS = [
    {'name': 'BTC', 'rel_threshold': 0.025, 'last': 30000, 'path': [WBTC, WETH, USDC], 'decimals': 8, 'router': SUSHISWAP},
    {'name': 'ETH', 'rel_threshold': 0.025, 'last': 3000, 'path': [WETH, USDC], 'decimals': 18, 'router': SUSHISWAP},
    # {'name': 'LUNA', 'rel_threshold': 0.05, 'last': 60, 'path': [LUNA, WETH, USDC], 'decimals': 18, 'router': SUSHISWAP},
    # {'name': 'CVX', 'rel_threshold': 0.05, 'last': 30, 'path': [CVX, WETH, USDC], 'decimals': 18, 'router': SUSHISWAP},
    # {'name': 'FXS', 'rel_threshold': 0.05, 'last': 60, 'path': [FXS, WETH, USDC], 'decimals': 18, 'router': SUSHISWAP},
]


def wait_for_next_block():
    if 'infura' in network.web3.manager.provider.endpoint_uri:
        latency = 5
    else:
        latency = 0.1

    last_block = chain[-1]
    next_block = last_block

    while next_block['number'] == last_block['number']:
        time.sleep(latency)
        next_block = chain[-1]

    return next_block


def get_price(token):
    USDC_AMOUNT_WEI = USDC_AMOUNT * 10**6
    amounts_in = token['router'].getAmountsIn(USDC_AMOUNT_WEI, token['path'])
    price = USDC_AMOUNT / (amounts_in[0] / 10 ** token['decimals'])
    return price


@pid.PidFile("price_alerts", piddir=os.getcwd())
def main():
    while True:
        block = wait_for_next_block()
        block_number = block['number']
        idx = block_number % BLOCK_RECORDS

        for token in TOKENS:
            price = get_price(token)

            if 'prices' not in token:
                token['prices'] = [price] * BLOCK_RECORDS
            else:
                token['prices'][idx] = price

            avg_price = sum(token['prices']) / len(token['prices'])
            price_change = abs(avg_price - token['last']) / token['last']

            if price_change > token['rel_threshold']:

                price_digits = int(math.log10(price)) + 1
                price_rounded = round(avg_price, max(0, 3 - price_digits))

                if avg_price < token['last']:
                    subject = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {token['name']} down: {price_rounded}"
                else:
                    subject = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} {token['name']} up: {price_rounded}"

                token['last'] = avg_price

                send_slack_msg(subject)


if __name__ == '__main__':
    try:
        main()
    except pid.base.PidFileAlreadyLockedError:
        sys.exit(0)
    except (SystemExit, KeyboardInterrupt) as e:
        sys.exit(e)
    except:
        raise