import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Validate proxy settings
proxy_server = os.getenv("PROXY_SERVER")
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")

if not all([proxy_server, proxy_username, proxy_password]):
    print("ERROR: Missing proxy configuration in .env file!")
    print(f"PROXY_SERVER loaded: {bool(proxy_server)}")
    print(f"PROXY_USERNAME loaded: {bool(proxy_username)}")
    print(f"PROXY_PASSWORD loaded: {bool(proxy_password)}")
    exit(1)

PROXY = {
    "server": proxy_server,
    "username": proxy_username,
    "password": proxy_password
}

print(f"Proxy configuration loaded: {proxy_server}")

URL = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/protocol/openid-connect/registrations?client_id=patient-de-client&context=navigation_bar&esid=b-oZcij7F6iVw0uFhGEz0IWr&from=%2Fsessions%2Fnew%3Fcontext%3Dnavigation_bar&nonce=8e5600e0efdbf97be45eb0274d0eb0bc&redirect_uri=https%3A%2F%2Fwww.doctolib.de%2Fauth%2Fpatient_de%2Fcallback&response_type=code&scope=openid+email&ssid=c138000win-cA1Yckyz62yC&state=e3283b453c570f44198198f43e11b372&ui_locales=de#step-username_sign_up"

async def stealth(page):
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    """)

async def run_instance(index):
    while True:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                    proxy=PROXY
                )

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    locale="de-DE",
                    viewport={"width": 1280, "height": 800},
                    timezone_id="Europe/Berlin",
                    geolocation={"latitude": 52.52, "longitude": 13.405},  # Berlin, Germany
                    permissions=["geolocation"]
                )

                page = await context.new_page()
                await stealth(page)

                print(f"[{index}] Opening page")
                await page.goto(URL, wait_until="networkidle")
                await page.wait_for_selector('.oxygen-input-field__input.text-ellipsis', timeout=15000)
                phone_number = f'+49151178831{index:02}'
                await page.fill('.oxygen-input-field__input.text-ellipsis', phone_number)

                await page.get_by_role("button", name="Weiter").click()
                await page.wait_for_timeout(50 * 1000)

                cookies = await context.cookies()
                dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)

                if dl_frcid:
                    print(f"[{index}] dl_frcid={dl_frcid}")
                    with open("cookies.txt", "a") as f:
                        f.write(f"{dl_frcid}\n")
                else:
                    print(f"[{index}] dl_frcid not found")

                await browser.close()
                await asyncio.sleep(3)  # Optional delay before restarting
        except Exception as e:
            print(f"[{index}] Error: {e}")
            await asyncio.sleep(5)  # Cooldown before retrying in case of error

async def main():
    tasks = [run_instance(i) for i in range(30)]
    await asyncio.gather(*tasks)
asyncio.run(main())