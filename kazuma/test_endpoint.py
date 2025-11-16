import requests
import json

# Test the evaluate-location endpoint
url = "http://localhost:8000/api/siting/evaluate-location"

# Near the Savoonga plant we just tested
payload = {
    "latitude": 63.695,
    "longitude": -170.476,
    "weight_clean": 0.4,
    "weight_transmission": 0.3,
    "weight_reliability": 0.3
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Nearby plants: {len(data.get('nearby_power_plants', []))}")
    for p in data.get('nearby_power_plants', [])[:5]:
        print(f"  - {p['plant_name']} ({p['distance_km']}km)")
else:
    print(f"Error: {response.text}")
