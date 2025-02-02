from flask import Flask, request, make_response
import hashlib
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# DeepSeek API ����
DEEPSEEK_API_KEY = "your-deepseek-api-key"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# ΢�� Token�����빫��ƽ̨����һ�£�
WECHAT_TOKEN = "your-wechat-token"

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
    response = requests.post(DEEPSEEK_ENDPOINT, json=payload, headers=headers)
    return response.json()["choices"][0]["message"]["content"]

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)