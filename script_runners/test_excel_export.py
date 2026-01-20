import requests
import json

def test_export():
    url = "http://localhost:5001/export_to_excel"
    data = {
        "rows": [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "London"],
            ["Charlie", "35", "Paris"]
        ]
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type')
            print(f"Content-Type: {content_type}")
            
            if 'spreadsheetml' in content_type:
                filename = "test_export.xlsx"
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"Successfully downloaded {filename}")
            else:
                print(f"Unexpected Content-Type: {content_type}")
                print(response.text)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_export()
