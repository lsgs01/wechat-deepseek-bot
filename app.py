import flask
from flask import Flask, request, make_response
import hashlib
import requests
import xml.etree.ElementTree as ET
import time
import os
import logging

app = Flask(__name__)

# ������־��¼
logging.basicConfig(level=logging.INFO)

# �ӻ��������л�ȡ DeepSeek API ����
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# �ӻ��������л�ȡ΢�� Token
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN")

# ��黷�������Ƿ���ȷ����
if DEEPSEEK_API_KEY is None or WECHAT_TOKEN is None:
    logging.error("DEEPSEEK_API_KEY �� WECHAT_TOKEN ��������δ���ã��������á�")
    raise ValueError("DEEPSEEK_API_KEY �� WECHAT_TOKEN ��������δ���ã��������á�")

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
        response.raise_for_status()  # ��������Ƿ�ɹ�
        return response.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        logging.error(f"DeepSeek API �������: {e}")
        return "��Ǹ����ʱ�޷���ȡ�ظ������Ժ����ԡ�"
    except (KeyError, IndexError):
        logging.error("���� DeepSeek API ��Ӧ����")
        return "��Ǹ����ʱ�޷���ȡ�ظ������Ժ����ԡ�"

@app.route('/wechat', methods=['GET', 'POST'])
def wechat_handler():
    if request.method == 'GET':
        # ��֤������
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        if verify_signature(signature, timestamp, nonce):
            return echostr
        else:
            return 'Verification Failed', 403
    else:
        # �����û���Ϣ
        try:
            xml_data = request.data
            root = ET.fromstring(xml_data)
            user_message = root.find('Content').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text

            # ���� DeepSeek
            ai_reply = get_deepseek_reply(user_message)

            # ���� XML ��Ӧ
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
            logging.error("����΢�� XML ��Ϣ����")
            return "��Ǹ����Ϣ�����������Ժ����ԡ�", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)