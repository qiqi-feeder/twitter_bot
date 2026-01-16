import requests
import os
from pathlib import Path
def test_media_upload():
    BASE_DIR = Path(__file__).resolve().parent.parent
    url = 'http://localhost:5000/tweet/post'
    
    # Use existing test image
    image_path = BASE_DIR / 'assets' / 'test.jpg'
    print(f"✅ Using test image: {image_path}")
    
    # Open the file for uploading
    # Use tuple list format: [(field_name, file_object)]
    files = [
        ('images', open(image_path, 'rb'))
    ]
    data = {
        'content': f'Test tweet with image - {int(__import__("time").time())}'
    }
    
    try:
        response = requests.post(url, data=data, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the file
        if files:
            for _, file_obj in files:
                file_obj.close()
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == '__main__':
    test_media_upload()
