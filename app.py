import flask
from flask import Flask, request, make_response
import hashlib
import requests
import xml.etree.ElementTree as ET
import time
import os
import logging

app = Flask(__name__)

# 配置日志记录
logging.basicConfig(level=logging.INFO)

# 从环境变量中获取 DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# 从环境变量中获取微信 Token
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN")

# 检查环境变量是否正确设置
if DEEPSEEK_API_KEY is None or WECHAT_TOKEN is None:
    logging.error("DEEPSEEK_API_KEY 或 WECHAT_TOKEN 环境变量未设置，请检查配置。")
    raise ValueError("DEEPSEEK_API_KEY 或 WECHAT_TOKEN 环境变量未设置，请检查配置。")

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
        response.raise_for_status()  # 检查请求是否成功
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        logging.error(f"DeepSeek API 请求出错: {e}")
        return "抱歉，暂时无法获取回复，请稍后再试。"
    except (KeyError, IndexError):
        logging.error("解析 DeepSeek API 响应出错。")
        return "抱歉，暂时无法获取回复，请稍后再试。"

@app.route('/wechat', methods=['GET', 'POST'])
def wechat_handler():
    if request.method == 'GET':
        # 验证服务器
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        if verify_signature(signature, timestamp, nonce):
            return echostr
        else:
            return 'Verification Failed', 403
    else:
        # 处理用户消息
        try:
            xml_data = request.data
            root = ET.fromstring(xml_data)
            user_message = root.find('Content').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text

            # 调用 DeepSeek
            ai_reply = get_deepseek_reply(user_message)

            # 返回 XML 响应
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
            logging.error("解析微信 XML 消息出错。")
            return "抱歉，消息解析出错，请稍后再试。", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)