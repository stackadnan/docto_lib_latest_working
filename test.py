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
    "cookie": "AUTH_SESSION_ID=0792a203-2437-4355-8c43-10b00da5d9f4.keycloak-patients-2-25837; AUTH_SESSION_ID_LEGACY=0792a203-2437-4355-8c43-10b00da5d9f4.keycloak-patients-2-25837; __cf_bm=6vgoE0NtZSiSpWRqVIuTLyTB4OEiJxPkPpxbV3R8y_8-1754044720-1.0.1.1-id6PPCbjEDZ3qJrd_ERvjKSP_f93Bv.B193Ysq9DIZCj_v879rQNBHCd0Q0bM_A2zoPE8eQBFZ2lejTbi5AanApBK7yWynKxy75Z_P0i.PkPlYT7lq3nO6XMLYxkV.yJ; _cfuvid=tsZpI73XcG1IXucXzzHM16y_ed52daSuWVsdHYFntYM-1754044720902-0.0.1.1-604800000; __cf_bm=0G.tO2LHLFW9nXydeC9NFoCMkq4tgqwEMHZfBvdzqn8-1754044721-1.0.1.1-W6uO1paJ65587rPeBjrRl7_pkEksheWdd3s5WVCInTwbMcI15lbsVDM7Uyn6ZXABFNV_.CXjNrjhNx.6489UXB4ED9s38phUU2cMvyN1fR_WYfCrwiWYBg2UvZ28GLGi; _cfuvid=U7CecjQyY6MPETu1RzO.i3.O81DDu93KxSwnBo.WdLw-1754044721974-0.0.1.1-604800000; dl_frcid=f6891a3c-945d-47db-93e5-dadad80014b9; _dd_s=aid=ff99c8ed-887a-4a4b-a6a2-a356eaa09e46&rum=0&expire=1754045623807"
}

response = requests.post(url, json=payload, headers=headers)

print(response.status_code)