import requests
import json
from datetime import datetime, timezone, timedelta

headers = {}
data = {
    'query': '{derData { solar(gwId: "01239e884755621dee") { latest { ts } } } }',
}

response = requests.post('https://api.srcful.dev', headers=headers, json=data)
response.raise_for_status()
print(response.status_code)
latestTimestamp = datetime.strptime(json.loads(response.content.decode('utf-8'))["data"]["derData"]["solar"]["latest"]["ts"], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
# latestTimestamp = datetime(2025, 5, 2, 5, 32, 47, 392000, tzinfo=timezone.utc) # test timestamp
currentTimestamp = datetime.now(timezone.utc)
print(latestTimestamp)
print(currentTimestamp)
difference = currentTimestamp - latestTimestamp
print(difference)
if currentTimestamp - latestTimestamp > timedelta(minutes=5):
    print("Offline")
else:
    print("Online")