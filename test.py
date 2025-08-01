import requests

url = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/accounts/check_existence"

payload = {
    "username": "+49 151 23456789",
    "clientId": "patient-de-client"
}

proxy = {
    "http": "r_c7c72217b5-country-de-sid-85fcde5e:9871a9d8a9@v2.proxyempire.io:5000",
    "https": "r_c7c72217b5-country-de-sid-85fcde5e:9871a9d8a9@v2.proxyempire.io:5000"
}

headers = {
    "host": "www.doctolib.de",
    "connection": "keep-alive",
    "sec-ch-ua-full-version-list": "\"Not)A;Brand\";v=\"8.0.0.0\", \"Chromium\";v=\"138.0.7204.184\", \"Google Chrome\";v=\"138.0.7204.184\"",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
    "sec-ch-ua-bitness": "\"64\"",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-arch": "\"x86\"",
    "sec-ch-ua-full-version": "\"138.0.7204.184\"",
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "sec-ch-ua-platform-version": "\"19.0.0\"",
    "origin": "https://www.doctolib.de",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "cookie": "_dd_s=aid=40a2cceb-c89e-429e-9fba-2e5ccf06e3e9&rum=0&expire=1754052158944"
}

response = requests.post(url, json=payload, headers=headers)

print(response.status_code)