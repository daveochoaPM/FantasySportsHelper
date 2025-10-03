
from slack_sdk import WebClient

def dm(token: str, user_id: str, text: str):
    client = WebClient(token=token)
    client.chat_postMessage(channel=user_id, text=text)
