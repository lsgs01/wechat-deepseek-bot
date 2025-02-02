import os
import time
import hashlib
import logging
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get environment variables
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN")

# Check if environment variables are set
if DEEPSEEK_API_KEY is None or WECHAT_TOKEN is None:
    logging.error("DEEPSEEK_API_KEY or WECHAT_TOKEN environment variable is not set. Please check the configuration.")
    logging.info("Hint: Create a .env file with DEEPSEEK_API_KEY and WECHAT_TOKEN.")
    raise ValueError("Required environment variables are missing.")

app = Flask(__name__)

def verify_signature(signature, timestamp, nonce):
    """
    Verify the signature from WeChat server.
    """
    # Check if timestamp is within 5 minutes
    current_time = int(time.time())
    if abs(current_time - int(timestamp)) > 300:  # 5 minutes
        logging.warning("Timestamp is out of range.")
        return False
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list).encode('utf-8')
    return hashlib.sha1(tmp_str).hexdigest() == signature

def get_deepseek_reply(user_message):
    """
    Get a reply from DeepSeek API.
    """
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

@app.route('/', methods=['GET', 'POST'])
def wechat_handler():
    """
    Handle WeChat server verification and user messages.
    """
    if request.method == 'GET':
        # Handle WeChat server verification
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        logging.info(f"Received GET request: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")
        if verify_signature(signature, timestamp, nonce):
            return echostr
        else:
            logging.warning("Signature verification failed.")
            return 'Verification Failed', 403
    else:
        # Handle user messages
        try:
            xml_data = request.data
            logging.info(f"Received POST request data: {xml_data}")
            root = ET.fromstring(xml_data)
            user_message = root.find('Content').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text
            logging.info(f"User message: {user_message}, From: {from_user}, To: {to_user}")

            # Call DeepSeek API to generate a reply
            ai_reply = get_deepseek_reply(user_message)
            logging.info(f"AI reply: {ai_reply}")

            # Return XML response to WeChat
            response_xml = f'''
            <xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{int(time.time())}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{ai_reply}]]></Content>
            </xml>
            '''
            logging.info(f"Response XML: {response_xml}")
            return response_xml
        except ET.ParseError:
            logging.error("Error parsing WeChat XML message.")
            return "Sorry, there was an error parsing the message. Please try again later.", 400
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return "Sorry, an unexpected error occurred. Please try again later.", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)