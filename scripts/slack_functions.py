import os
import ssl
import configparser
from slack import WebClient


def send_slack_msg(text, channel="#general"):
    home_path = os.getenv('HOME')
    config = configparser.ConfigParser()
    config.read(f"{home_path}/config.ini")
    slack_api_key = config['SLACK']['slack_api_key']

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    slack_client = WebClient(slack_api_key, ssl=ssl_context)
    slack_client.chat_postMessage(channel=channel, text=text)


def slack_link(url, text):
    return f'<{url}|{text}>'


if __name__ == '__main__':
    send_slack_msg("This is a test message")