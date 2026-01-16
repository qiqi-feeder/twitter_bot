import requests
import time

def test_text_post():
    url = 'http://localhost:5000/tweet/post'

    data = {
        'content': f'hello - {int(time.time())}'
    }

    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")

        # 打印原始返回，避免 JSON 解析错误
        print("Raw Response:")
        print(response.text)

        # 如果是 JSON，再解析
        if response.headers.get('Content-Type', '').startswith('application/json'):
            print("Parsed JSON:")
            print(response.json())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_text_post()
