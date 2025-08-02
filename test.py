import requests
import random
import uuid
import time

def generate_realistic_headers():
    """Generate realistic headers with randomized fingerprinting"""
    
    # Different Chrome versions
    chrome_versions = [
        "138.0.7204.184",
        "138.0.7204.150",
        "137.0.6956.122",
        "137.0.6956.99",
        "136.0.6957.124",
        "136.0.6957.99"
    ]
    
    # Different platform versions
    platform_versions = [
        "19.0.0",
        "15.0.0", 
        "10.0.0",
        "13.0.0"
    ]
    
    # Different architectures (realistic for Windows)
    architectures = ["x86", "arm"]
    
    # Different bitness
    bitness_options = ["64", "32"]
    
    # Accept language variations
    languages = [
        "en-US,en;q=0.9",
        "de-DE,de;q=0.9,en;q=0.8",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,de;q=0.8",
        "de,en-US;q=0.9,en;q=0.8"
    ]
    
    # Select random values
    chrome_version = random.choice(chrome_versions)
    major_version = chrome_version.split('.')[0]
    platform_version = random.choice(platform_versions)
    arch = random.choice(architectures)
    bitness = random.choice(bitness_options)
    language = random.choice(languages)
    
    # Generate random session ID components
    session_id = f"c{random.randint(100000, 999999)}win-{random.choice(['cA1Y', 'bX2Z', 'dR3W', 'eT4V'])}{random.choice(['ckyz', 'mnop', 'qrst', 'uvwx'])}{random.randint(10, 99)}{random.choice(['yC', 'zD', 'aE', 'bF'])}"
    
    # Generate random UUID for dl_frcid
    dl_frcid = "e42f8fb8-eda3-4641-815d-3e7aafab9ff6"
    
    # Generate random datadog session
    dd_aid = str(uuid.uuid4())
    dd_expire = int(time.time() * 1000) + random.randint(3600000, 7200000)  # 1-2 hours from now
    
    headers = {
        "host": "www.doctolib.de",
        "connection": "keep-alive",
        "sec-ch-ua-full-version-list": f"\"Not)A;Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"{chrome_version}\", \"Google Chrome\";v=\"{chrome_version}\"",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-ch-ua": f"\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"{major_version}\", \"Google Chrome\";v=\"{major_version}\"",
        "sec-ch-ua-bitness": f"\"{bitness}\"",
        "sec-ch-ua-model": "\"\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-arch": f"\"{arch}\"",
        "sec-ch-ua-full-version": f"\"{chrome_version}\"",
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version.split('.')[0]}.0.0.0 Safari/537.36",
        "sec-ch-ua-platform-version": f"\"{platform_version}\"",
        "origin": "https://www.doctolib.de",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": language,
        "cookie": f"ssid={session_id}; locale=de; didomi_token=eyJ1c2VyX2lkIjoiMTk4NDg1YzEtZDA3YS02YzhkLWJiNjktMDUxM2QwNjc4OGMwIiwiY3JlYXRlZCI6IjIwMjUtMDctMjZUMjA6MTA6NTMuMDYzWiIsInVwZGF0ZWQiOiIyMDI1LTA3LTI2VDIwOjExOjAxLjgxM1oiLCJ2ZW5kb3JzIjp7ImRpc2FibGVkIjpbImM6ZG9jdG9saWJuLVdwODdDcFhBIiwiYzpkb2N0b2xpYi1yQWhFM3l0OSIsImM6ZG9jdG9saWJhLXRndGIzVzhQIl19LCJwdXJwb3NlcyI6eyJkaXNhYmxlZCI6WyJhZHNwZXJmb3ItenhZcmhMVGQiLCJhbmFseXRpY3MtTkdxeFdibW4iLCJhbmFseXRpay1OMlpIOUJxUSIsImRpc3BsYXl0YS1WOGtNZW5ZYSIsImRpc3BsYXl0YS1WclBQVm5IaCIsImFuYWx5dGljcy1QOFlHajdESCJdfSwidmVyc2lvbiI6Mn0=; euconsent-v2=CQVKQkAQVKQkAAHABBENB0FgAAAAAAAAAAAAAAAAAAAA.YAAAAAAAAAAA; dl_frcid={dl_frcid}; _dd_s=aid={dd_aid}&rum=0&expire={dd_expire}"
    }
    
    return headers

url = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/accounts/check_existence"

payload = {
    "username": "+49 151 23456789",
    "clientId": "patient-de-client"
}

proxy = {
    "http": "r_c7c72217b5-country-de-sid-85fcde5e:9871a9d8a9@v2.proxyempire.io:5000",
    "https": "r_c7c72217b5-country-de-sid-85fcde5e:9871a9d8a9@v2.proxyempire.io:5000"
}

# Generate realistic headers each time
headers = generate_realistic_headers()

# Print some header info to see the randomization
print("Generated headers:")
print(f"Chrome Version: {headers['sec-ch-ua-full-version']}")
print(f"Architecture: {headers['sec-ch-ua-arch']}")
print(f"Language: {headers['accept-language']}")
print(f"Platform Version: {headers['sec-ch-ua-platform-version']}")
print(f"Session ID: {headers['cookie'].split(';')[0]}")
print("-" * 50)

response = requests.post(url, json=payload, headers=headers, proxies=proxy)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {response.json()}")
else:
    print(f"Error Response: {response.text}")

# Test multiple requests with different headers
print("\n" + "="*50)
print("Testing multiple requests with different fingerprints:")
print("="*50)

for i in range(3):
    print(f"\nRequest {i+1}:")
    headers = generate_realistic_headers()
    print(f"Chrome Version: {headers['sec-ch-ua-full-version']}")
    print(f"Architecture: {headers['sec-ch-ua-arch']}")
    print(f"Language: {headers['accept-language']}")
    
    response = requests.post(url, json=payload, headers=headers, proxies=proxy)
    print(f"Status Code: {response.status_code}")
    
    time.sleep(1)  # Small delay between requests