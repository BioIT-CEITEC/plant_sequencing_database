import requests
import json

url = "http://127.0.0.1:5000/api/upload"
file_path = "sample/synthetic_manuscript_1.pdf"

print("Starting upload and extraction...")
try:
    with open(file_path, "rb") as f:
        # stream=True is needed to capture Server-Sent Events as they arrive
        response = requests.post(url, files={"file": f}, stream=True)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            exit(1)
            
        print("Connected to stream. Waiting for events...")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = json.loads(decoded_line[6:])
                    stage = data.get('stage')
                    if stage == 'extracting_group':
                        print(f"[{data.get('progress')}] Extracting group: {data.get('group')}")
                    elif stage == 'group_complete':
                        print(f"Group complete: {data.get('group')}")
                    elif stage == 'complete':
                        print("Extraction complete!")
                    elif stage == 'error':
                        print(f"Error: {data.get('message')}")
                    else:
                        print(f"Event: {stage} - {data.get('message', '')}")
except Exception as e:
    print(f"Exception: {e}")
