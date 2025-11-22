import requests
import os

def test_media_upload():
    url = 'http://localhost:5000/tweet/post'
    
    # Create a dummy image file
    image_path = 'test_image.jpg'
    with open(image_path, 'wb') as f:
        f.write(os.urandom(1024))  # 1KB dummy file
    
    files = {
        'images': open(image_path, 'rb')
    }
    data = {
        'content': 'Test tweet with image via API'
    }
    
    try:
        response = requests.post(url, data=data, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        files['images'].close()
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == '__main__':
    test_media_upload()
