#!/usr/bin/env python3
"""
Simple test script to verify API endpoints and cookie validity
"""
import asyncio
import aiohttp
import sys

# Fix for Windows aiodns issue
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test_api():
    """Test both French and German APIs with a sample cookie"""
    
    # Read first cookie
    try:
        with open('cookies.txt', 'r') as f:
            cookie = f.readline().strip()
            print(f"Testing with cookie: {cookie[:8]}...")
    except Exception as e:
        print(f"Error reading cookies: {e}")
        return
    
    # Test phone numbers - use appropriate formats
    french_phone = "+33123456789"  # French format
    german_phone = "+4915117881953"  # German format (from your logs)
    
    # French API test
    print("\n=== Testing French API (doctolib.fr) ===")
    french_url = "https://www.doctolib.fr/booking/api/accounts/check_mobile_number.json"
    french_payload = {"mobile_number": french_phone, "send_sms": False}
    french_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.85 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": f"dl_frcid={cookie}",
        "Origin": "https://www.doctolib.fr",
        "Referer": "https://www.doctolib.fr/"
    }
    
    # German API test  
    print("\n=== Testing German API (doctolib.de) ===")
    german_url = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/accounts/check_existence"
    german_payload = {"username": german_phone, "clientId": "patient-de-client"}
    german_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.85 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": f"dl_frcid={cookie}",
        "Origin": "https://www.doctolib.de",
        "Referer": "https://www.doctolib.de/"
    }
    
    async with aiohttp.ClientSession() as session:
        # Test French API
        try:
            async with session.post(french_url, json=french_payload, headers=french_headers, timeout=10) as response:
                print(f"French API Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"French API Response: {data}")
                elif response.status == 401:
                    print("French API: 401 Unauthorized (cookie invalid for French site)")
                else:
                    text = await response.text()
                    print(f"French API Response ({response.status}): {text[:200]}")
        except Exception as e:
            print(f"French API Error: {e}")
        
        # Test German API
        try:
            async with session.post(german_url, json=german_payload, headers=german_headers, timeout=10) as response:
                print(f"German API Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"German API Response: {data}")
                elif response.status == 401:
                    print("German API: 401 Unauthorized (cookie invalid for German site)")
                else:
                    text = await response.text()
                    print(f"German API Response ({response.status}): {text[:200]}")
        except Exception as e:
            print(f"German API Error: {e}")

if __name__ == "__main__":
    print("API Endpoint Test")
    print(f"Platform: {sys.platform}")
    asyncio.run(test_api())
