import flask
from flask import Flask, request, make_response
import hashlib
import requests
import xml.etree.ElementTree as ET
import time
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get DeepSeek API configuration from environment variables
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# Get WeChat Token from environment variables
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN")

# Check if environment variables are set correctly
if DEEPSEEK_API_KEY is None or WECHAT_TOKEN is None:
    logging.error("DEEPSEEK_API_KEY or WECHAT_TOKEN environment variable is not set. Please check the configuration.")
    raise ValueError("DEEPSEEK_API_KEY or WECHAT_TOKEN environment variable is not set. Please check the configuration.")


def verify_signature(signature, timestamp, nonce):
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list).encode('utf-8')
    return hashlib.sha1(tmp_str).hexdigest() == signature


def get_deepseek_reply(user_message):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_message}]
    }
    try:
        response = requests.post(DEEPSEEK_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()  # Check if the request was successful
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        logging.error(f"DeepSeek API request error: {e}")
        return "Sorry, unable to get a reply at the moment. Please try again later."
    except (KeyError, IndexError):
        logging.error("Error parsing DeepSeek API response.")
        return "Sorry, unable to get a reply at the moment. Please try again later."


@app.route('/wechat', methods=['GET', 'POST'])
def wechat_handler():
    if request.method == 'GET':
        # Verify the server
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        if verify_signature(signature, timestamp, nonce):
            return echostr
        else:
            return 'Verification Failed', 403
    else:
        # Process user messages
        try:
            xml_data = request.data
            root = ET.fromstring(xml_data)
            user_message = root.find('Content').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text

            # Call DeepSeek
            ai_reply = get_deepseek_reply(user_message)

            # Return XML response
            return f'''
            <xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{int(time.time())}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{ai_reply}]]></Content>
            </xml>
            '''
        except ET.ParseError:
            logging.error("Error parsing WeChat XML message.")
            return "Sorry, there was an error parsing the message. Please try again later.", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)