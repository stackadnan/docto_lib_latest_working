import asyncio
import os
import random
import logging
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Global file lock for thread-safe operations
_file_lock = threading.Lock()
_processed_numbers = set()  # Track processed numbers to prevent duplicates

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('play_write_logs.txt', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate proxy settings
proxy_server = os.getenv("PROXY_SERVER")
proxy_username = os.getenv("PROXY_USERNAME")
proxy_password = os.getenv("PROXY_PASSWORD")

if not all([proxy_server, proxy_username, proxy_password]):
    logger.error("Missing proxy configuration in .env file!")
    logger.error(f"PROXY_SERVER loaded: {bool(proxy_server)}")
    logger.error(f"PROXY_USERNAME loaded: {bool(proxy_username)}")
    logger.error(f"PROXY_PASSWORD loaded: {bool(proxy_password)}")
    exit(1)

PROXY = {
    "server": proxy_server,
    "username": proxy_username,
    "password": proxy_password
}

logger.info(f"Proxy configuration loaded: {proxy_server}")

URL = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/protocol/openid-connect/registrations?client_id=patient-de-client&context=navigation_bar&esid=b-oZcij7F6iVw0uFhGEz0IWr&from=%2Fsessions%2Fnew%3Fcontext%3Dnavigation_bar&nonce=8e5600e0efdbf97be45eb0274d0eb0bc&redirect_uri=https%3A%2F%2Fwww.doctolib.de%2Fauth%2Fpatient_de%2Fcallback&response_type=code&scope=openid+email&ssid=c138000win-cA1Yckyz62yC&state=e3283b453c570f44198198f43e11b372&ui_locales=de#step-username_sign_up"

# Fingerprint pools for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
    {"width": 1680, "height": 1050},
    {"width": 1024, "height": 768}
]

TIMEZONES = [
    "Europe/Berlin",
    "Europe/London", 
    "Europe/Paris",
    "Europe/Rome",
    "Europe/Madrid",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Vienna"
]

LOCALES = [
    "de-DE",
    "en-GB", 
    "fr-FR",
    "it-IT",
    "es-ES",
    "nl-NL"
]

LANGUAGES_SETS = [
    ['de-DE', 'de', 'en'],
    ['en-GB', 'en', 'de'],
    ['fr-FR', 'fr', 'en'],
    ['it-IT', 'it', 'en'],
    ['es-ES', 'es', 'en'],
    ['nl-NL', 'nl', 'en']
]

# German city coordinates for geolocation variety
GEOLOCATIONS = [
    {"latitude": 52.52, "longitude": 13.405},  # Berlin
    {"latitude": 53.5511, "longitude": 9.9937},  # Hamburg
    {"latitude": 48.1351, "longitude": 11.5820},  # Munich
    {"latitude": 50.1109, "longitude": 8.6821},  # Frankfurt
    {"latitude": 51.2277, "longitude": 6.7735},  # Düsseldorf
    {"latitude": 50.9375, "longitude": 6.9603},  # Cologne
    {"latitude": 48.7758, "longitude": 9.1829},  # Stuttgart
    {"latitude": 51.0504, "longitude": 13.7373}   # Dresden
]

def get_random_fingerprint():
    """Generate a random browser fingerprint for each request"""
    languages = random.choice(LANGUAGES_SETS)
    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": random.choice(VIEWPORTS),
        "timezone": random.choice(TIMEZONES),
        "locale": random.choice(LOCALES),
        "geolocation": random.choice(GEOLOCATIONS),
        "languages": languages
    }

async def check_registration_status(page, phone_number, index):
    """
    Check if phone number is registered by looking for specific text patterns
    Returns: 'registered', 'not_registered', 'cookie_found', or 'error'
    """
    try:
        # Wait a bit after clicking Weiter
        await asyncio.sleep(random.uniform(2, 4))
        
        # First check for progress bar (FRC progress) with dynamic waiting
        try:
            progress_element = await page.wait_for_selector('.frc-progress', timeout=3000)
            if progress_element:
                logger.info(f"[{index}] 🔄 Progress bar detected, starting dynamic monitoring...")
                
                # Dynamic progress monitoring with staged waiting approach
                stage_duration = 8  # Each stage is 8 seconds
                max_stages = 50  # Maximum 50 stages (400 seconds total)
                current_stage = 1
                progress_complete = False
                last_progress_value = None
                progress_stuck_count = 0
                overall_start_time = asyncio.get_event_loop().time()
                
                while not progress_complete and current_stage <= max_stages:
                    stage_start_time = asyncio.get_event_loop().time()
                    logger.info(f"[{index}] 📅 Starting progress monitoring stage {current_stage}/{max_stages} ({stage_duration} seconds each)")
                    
                    # Monitor for this stage duration (30 seconds)
                    while not progress_complete and (asyncio.get_event_loop().time() - stage_start_time) < stage_duration:
                        try:
                            # Method 1: Check if progress element still exists
                            progress_elements = await page.query_selector_all('.frc-progress')
                            if not progress_elements:
                                logger.info(f"[{index}] ✅ Progress bar disappeared (method 1: element removed) - Stage {current_stage}")
                                progress_complete = True
                                break
                            
                            # Method 2: Check progress text content
                            progress_text = ""
                            for element in progress_elements:
                                try:
                                    text = await element.inner_text()
                                    if text:
                                        progress_text += text + " "
                                except:
                                    continue
                            
                            progress_text = progress_text.strip()
                            if progress_text:
                                logger.info(f"[{index}] 📊 Stage {current_stage} - Progress status: {progress_text}")
                                
                                # Check for completion indicators in text
                                completion_indicators = ["100%", "complete", "completed", "fertig", "done", "finished", "vollständig"]
                                if any(indicator in progress_text.lower() for indicator in completion_indicators):
                                    logger.info(f"[{index}] ✅ Progress completed (method 2: completion text found) - Stage {current_stage}")
                                    progress_complete = True
                                    break
                            
                            # Method 3: Check progress bar value/aria attributes
                            for element in progress_elements:
                                try:
                                    # Check aria-valuenow attribute
                                    aria_value = await element.get_attribute('aria-valuenow')
                                    if aria_value:
                                        current_value = float(aria_value)
                                        aria_max = await element.get_attribute('aria-valuemax') or "100"
                                        max_value = float(aria_max)
                                        progress_percent = (current_value / max_value) * 100
                                        
                                        logger.info(f"[{index}] 📈 Stage {current_stage} - Progress: {progress_percent:.1f}% ({current_value}/{max_value})")
                                        
                                        if progress_percent >= 100:
                                            logger.info(f"[{index}] ✅ Progress completed (method 3: aria-valuenow = 100%) - Stage {current_stage}")
                                            progress_complete = True
                                            break
                                        
                                        # Check if progress is stuck
                                        if last_progress_value == current_value:
                                            progress_stuck_count += 1
                                            if progress_stuck_count > 20:  # Stuck for more than 10 seconds
                                                logger.warning(f"[{index}] ⚠️ Stage {current_stage} - Progress appears stuck at {progress_percent:.1f}%, checking completion...")
                                                # Wait a bit more and check if element disappears
                                                await asyncio.sleep(2)
                                                remaining_elements = await page.query_selector_all('.frc-progress')
                                                if not remaining_elements:
                                                    logger.info(f"[{index}] ✅ Progress completed (method 3: stuck but element removed) - Stage {current_stage}")
                                                    progress_complete = True
                                                    break
                                        else:
                                            progress_stuck_count = 0
                                            last_progress_value = current_value
                                except:
                                    continue
                            
                            # Method 4: Check CSS classes for completion
                            for element in progress_elements:
                                try:
                                    class_name = await element.get_attribute('class') or ""
                                    if any(cls in class_name.lower() for cls in ['complete', 'finished', 'done', 'success']):
                                        logger.info(f"[{index}] ✅ Progress completed (method 4: completion class found) - Stage {current_stage}")
                                        progress_complete = True
                                        break
                                except:
                                    continue
                            
                            # Method 5: Check for style attributes indicating completion
                            for element in progress_elements:
                                try:
                                    style = await element.get_attribute('style') or ""
                                    if 'width: 100%' in style or 'width:100%' in style:
                                        logger.info(f"[{index}] ✅ Progress completed (method 5: width 100% in style) - Stage {current_stage}")
                                        progress_complete = True
                                        break
                                except:
                                    continue
                            
                            if progress_complete:
                                break
                                
                            # Adaptive delay based on progress
                            if last_progress_value and last_progress_value > 50:
                                # Progress is high, check more frequently
                                await asyncio.sleep(0.3)
                            else:
                                # Progress is low, check less frequently
                                await asyncio.sleep(0.8)
                            
                        except Exception as e:
                            logger.error(f"[{index}] ⚠️ Stage {current_stage} - Error in progress monitoring: {e}")
                            # If there's an error, wait a bit and check if element still exists
                            await asyncio.sleep(1)
                            try:
                                remaining_elements = await page.query_selector_all('.frc-progress')
                                if not remaining_elements:
                                    logger.info(f"[{index}] ✅ Progress completed (error recovery: element disappeared) - Stage {current_stage}")
                                    progress_complete = True
                                    break
                            except:
                                pass
                    
                    if not progress_complete:
                        stage_elapsed = asyncio.get_event_loop().time() - stage_start_time
                        logger.info(f"[{index}] ⏱️ Stage {current_stage} completed ({stage_elapsed:.1f}s) - Progress still running, moving to next stage...")
                        current_stage += 1
                        
                        # Brief pause between stages
                        await asyncio.sleep(0.5)
                
                # Final completion handling
                if progress_complete:
                    total_elapsed = asyncio.get_event_loop().time() - overall_start_time
                    logger.info(f"[{index}] 🎯 Progress monitoring completed successfully after {total_elapsed:.1f}s (Stage {current_stage})")
                    # Wait a moment for any final page updates
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    # Check for cookies after progress completion
                    cookies = await page.context.cookies()
                    dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)
                    if dl_frcid:
                        logger.info(f"[{index}] 🍪 Cookie found after progress completion: {dl_frcid}")
                        return 'cookie_found'
                    else:
                        logger.info(f"[{index}] 📝 Progress completed but no cookie found yet, continuing with normal checks...")
                else:
                    total_elapsed = asyncio.get_event_loop().time() - overall_start_time
                    logger.warning(f"[{index}] ⏰ Progress monitoring timeout after {total_elapsed:.1f}s ({max_stages} stages completed)")
                    # Still continue with normal checks even after timeout
        except:
            pass  # No progress bar found, continue with normal checks
        
        # First check for cookies immediately (if no progress bar)
        cookies = await page.context.cookies()
        dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)
        if dl_frcid:
            logger.info(f"[{index}] 🍪 Cookie found: {dl_frcid}")
            return 'cookie_found'
        
        # Check for "Wie heißen Sie?" text (indicates not registered)
        try:
            # Try multiple selectors for the "Wie heißen Sie?" text
            wie_heissen_selectors = [
                'text=Wie heißen Sie?',
                '[data-testid*="name"]',
                'input[placeholder*="Vorname"]',
                'input[placeholder*="Nachname"]',
                'text=Vorname',
                'text=Nachname'
            ]
            
            for selector in wie_heissen_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        logger.info(f"[{index}] ❌ Phone {phone_number} - NOT REGISTERED (found '{selector}')")
                        # Save to not_registered.txt and remove from phone_numbers.txt
                        save_phone_result(phone_number, False)
                        remove_phone_from_file(phone_number)
                        return 'not_registered'
                except:
                    continue
        except:
            pass
        
        # Check for popup with "Wir haben ein existierendes Konto gefunden" (indicates registered)
        try:
            # Try multiple selectors for existing account popup
            existing_account_selectors = [
                'text=Wir haben ein existierendes Konto gefunden',
                'text=existierendes Konto',
                'text=Konto gefunden',
                '[role="dialog"]',
                '.modal',
                '.popup'
            ]
            
            for selector in existing_account_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element:
                        # Double check by looking for text content
                        text_content = await element.text_content() if hasattr(element, 'text_content') else ""
                        if "existierendes" in text_content.lower() or "konto" in text_content.lower():
                            logger.info(f"[{index}] ✅ Phone {phone_number} - REGISTERED (found existing account)")
                            # Save to registered.txt and remove from phone_numbers.txt
                            save_phone_result(phone_number, True)
                            remove_phone_from_file(phone_number)
                            
                            # Instead of going back, click on the 6th dl-button-label to continue
                            try:
                                logger.info(f"[{index}] 🔄 Clicking 6th dl-button-label to continue with next number...")
                                button_elements = await page.query_selector_all('.dl-button-label')
                                if len(button_elements) >= 6:
                                    await button_elements[5].click()  # 6th element (0-indexed)
                                    await asyncio.sleep(random.uniform(1, 2))
                                    logger.info(f"[{index}] ✅ Successfully clicked 6th dl-button-label")
                                    return 'registered_continue'  # New status to indicate we can continue
                                else:
                                    logger.warning(f"[{index}] ⚠️ Only found {len(button_elements)} dl-button-label elements, expected at least 6")
                                    return 'registered'  # Fall back to normal registered handling
                            except Exception as e:
                                logger.error(f"[{index}] ❌ Error clicking 6th dl-button-label: {e}")
                                return 'registered'  # Fall back to normal registered handling
                except:
                    continue
        except:
            pass
        
        # Additional check: Look for any error messages or redirects
        try:
            # Check if we're still on the same page or redirected
            current_url = page.url
            if "registrations" not in current_url:
                logger.info(f"[{index}] 🔄 Redirected to: {current_url}")
                # Check cookies again after potential redirect
                cookies = await page.context.cookies()
                dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)
                if dl_frcid:
                    logger.info(f"[{index}] 🍪 Cookie found after redirect: {dl_frcid}")
                    return 'cookie_found'
        except:
            pass
        
        # If nothing found, return error to try again
        logger.warning(f"[{index}] ⚠️ No clear status detected for {phone_number}, will retry...")
        return 'error'
        
    except Exception as e:
        logger.error(f"[{index}] ❌ Error checking registration status: {e}")
        return 'error'

async def go_back_and_retry(page, index):
    """Go back to the previous page and clear the input field"""
    try:
        logger.info(f"[{index}] ⬅️ Going back to retry...")
        await page.go_back()
        await asyncio.sleep(random.uniform(1, 2))
        
        # Wait for the input field and clear it properly
        input_selector = '.oxygen-input-field__input.text-ellipsis'
        await page.wait_for_selector(input_selector, timeout=10000)
        
        # Multiple methods to ensure field is cleared
        await page.click(input_selector)  # Focus the field
        await asyncio.sleep(0.2)
        await page.keyboard.press('Control+a')  # Select all text
        await asyncio.sleep(0.1)
        await page.keyboard.press('Delete')  # Delete selected text
        await asyncio.sleep(random.uniform(0.5, 1))
        
        logger.debug(f"[{index}] Successfully went back and cleared input field")
        return True
    except Exception as e:
        logger.error(f"[{index}] ❌ Error going back: {e}")
        return False

def get_next_phone_number():
    """Get the next phone number from results/phone_numbers.txt (thread-safe)"""
    global _processed_numbers
    
    with _file_lock:
        try:
            if not os.path.exists("results/phone_numbers.txt"):
                logger.warning("Phone numbers file not found: results/phone_numbers.txt")
                return None
                
            with open("results/phone_numbers.txt", "r", encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            if not lines:
                logger.warning("No phone numbers available in results/phone_numbers.txt")
                return None
                
            # Find first number that hasn't been processed yet
            for phone_number in lines:
                if phone_number not in _processed_numbers:
                    _processed_numbers.add(phone_number)
                    logger.debug(f"Retrieved next phone number: {phone_number} (Remaining: {len(lines) - len(_processed_numbers)})")
                    return phone_number
            
            logger.warning("All phone numbers in file have been processed")
            return None
        except Exception as e:
            logger.error(f"Error reading phone numbers: {e}")
            return None

def remove_phone_from_file(phone_number):
    """Remove a phone number from results/phone_numbers.txt (thread-safe)"""
    with _file_lock:
        try:
            if not os.path.exists("results/phone_numbers.txt"):
                logger.warning("Phone numbers file not found for removal")
                return False
                
            with open("results/phone_numbers.txt", "r", encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            if phone_number not in lines:
                logger.warning(f"Phone number {phone_number} not found in file for removal")
                return False
                
            # Remove the phone number
            lines.remove(phone_number)
            
            # Write back to file
            with open("results/phone_numbers.txt", "w", encoding='utf-8') as f:
                if lines:
                    f.write("\n".join(lines) + "\n")
                else:
                    f.write("")  # Empty file
                    
            logger.info(f"Removed {phone_number} from phone_numbers.txt. Remaining: {len(lines)}")
            return True
        except Exception as e:
            logger.error(f"Error removing phone number {phone_number}: {e}")
            return False

def save_phone_result(phone_number, is_registered):
    """Save phone number to appropriate result file (thread-safe, prevents duplicates)"""
    with _file_lock:
        try:
            # Ensure results directory exists
            os.makedirs("results", exist_ok=True)
            
            if is_registered:
                result_file = "results/registered.txt"
                status = "REGISTERED"
            else:
                result_file = "results/not_registered.txt"
                status = "NOT REGISTERED"
            
            # Check if number already exists in the file to prevent duplicates
            existing_numbers = set()
            if os.path.exists(result_file):
                with open(result_file, "r", encoding='utf-8') as f:
                    existing_numbers = {line.strip() for line in f if line.strip()}
            
            if phone_number in existing_numbers:
                logger.warning(f"Phone number {phone_number} already exists in {result_file}, skipping duplicate")
                return True
                
            # Append to file only if not duplicate
            with open(result_file, "a", encoding='utf-8') as f:
                f.write(f"{phone_number}\n")
                
            logger.info(f"Saved {phone_number} as {status}")
            return True
        except Exception as e:
            logger.error(f"Error saving {phone_number}: {e}")
            return False

async def stealth(page, languages):
    """Enhanced stealth function with randomized properties"""
    plugins_count = random.randint(3, 8)
    webgl_vendor = random.choice(['Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Google Inc.'])
    webgl_renderer = random.choice([
        'Intel Iris OpenGL Engine',
        'NVIDIA GeForce GTX 1060',
        'AMD Radeon Pro 560',
        'Google SwiftShader'
    ])
    
    await page.add_init_script(f"""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
        
        // Add chrome object
        window.chrome = {{ runtime: {{}} }};
        
        
        // Randomize plugins
        Object.defineProperty(navigator, 'plugins', {{ get: () => new Array({plugins_count}).fill().map(() => ({{}})) }});
        
        // Randomize WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{webgl_vendor}';
            if (parameter === 37446) return '{webgl_renderer}';
            return getParameter.call(this, parameter);
        }};
        
        // Randomize canvas fingerprint
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const context = this.getContext('2d');
            if (context) {{
                context.fillStyle = 'rgba({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)}, 0.01)';
                context.fillRect(0, 0, 1, 1);
            }}
            return originalToDataURL.apply(this, args);
        }};
        
        // Hide automation indicators
        Object.defineProperty(navigator, 'permissions', {{
            get: () => ({{
                query: () => Promise.resolve({{ state: 'granted' }})
            }})
        }});
    """)

async def run_instance(index):
    logger.info(f"[{index}] Instance started")
    while True:
        try:
            # Get random fingerprint for this request
            fingerprint = get_random_fingerprint()
            
            logger.info(f"[{index}] Using fingerprint: {fingerprint['user_agent'][:50]}...")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        f"--user-agent={fingerprint['user_agent']}"
                    ],
                    proxy=PROXY
                )

                context = await browser.new_context(
                    user_agent=fingerprint['user_agent'],
                    locale=fingerprint['locale'],
                    viewport=fingerprint['viewport'],
                    timezone_id=fingerprint['timezone'],
                    geolocation=fingerprint['geolocation'],
                    permissions=["geolocation"]
                )

                page = await context.new_page()
                await stealth(page, fingerprint['languages'])

                logger.info(f"[{index}] Opening page with {fingerprint['viewport']['width']}x{fingerprint['viewport']['height']} viewport")
                await page.goto(URL, wait_until="networkidle")
                
                # Add random delay to mimic human behavior
                await asyncio.sleep(random.uniform(1, 3))
                
                await page.wait_for_selector('.oxygen-input-field__input.text-ellipsis', timeout=15000)
                logger.debug(f"[{index}] Input field found and ready")
                
                # Main retry loop for testing phone numbers
                max_attempts = 5  # Maximum attempts per browser instance
                attempt = 0
                cookie_found = False
                
                while attempt < max_attempts and not cookie_found:
                    attempt += 1
                    
                    # Get next phone number from file
                    phone_number = get_next_phone_number()
                    if not phone_number:
                        logger.warning(f"[{index}] 📱 No more phone numbers available in file")
                        break
                        
                    logger.info(f"[{index}] Attempt {attempt}/{max_attempts} - Testing phone: {phone_number}")
                    
                    # Add random delay before typing
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    # Clear field if this is a retry
                    if attempt > 1:
                        input_selector = '.oxygen-input-field__input.text-ellipsis'
                        await page.click(input_selector)  # Focus the field
                        await asyncio.sleep(0.2)
                        await page.keyboard.press('Control+a')  # Select all text
                        await asyncio.sleep(0.1)
                        await page.keyboard.press('Delete')  # Delete selected text
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                        logger.debug(f"[{index}] Input field cleared for retry")
                    
                    await page.fill('.oxygen-input-field__input.text-ellipsis', phone_number)
                    logger.debug(f"[{index}] Phone number entered: {phone_number}")

                    # Random delay before clicking
                    await asyncio.sleep(random.uniform(0.8, 2))
                    
                    await page.get_by_role("button", name="Weiter").click()
                    logger.debug(f"[{index}] Weiter button clicked")

                    await asyncio.sleep(random.uniform(0.8, 2))
                    
                    # Check registration status
                    status = await check_registration_status(page, phone_number, index)
                    logger.info(f"[{index}] Registration status for {phone_number}: {status}")
                    
                    if status == 'cookie_found':
                        # Save cookie and exit loop
                        cookies = await context.cookies()
                        dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)
                        if dl_frcid:
                            with open("cookies.txt", "a") as f:
                                f.write(f"{dl_frcid}\n")
                            logger.info(f"[{index}] 🎉 Cookie saved: {dl_frcid}")
                            cookie_found = True
                            break
                    
                    elif status == 'registered_continue':
                        # Number saved and removed, 6th dl-button-label clicked, input field should be ready
                        # No need to go back, just clear field and continue with next number
                        logger.info(f"[{index}] 🔄 Registered number handled, clearing field for next number...")
                        try:
                            # Wait for input field to be ready and clear it
                            input_selector = '.oxygen-input-field__input.text-ellipsis'
                            await page.wait_for_selector(input_selector, timeout=5000)
                            await page.click(input_selector)
                            await asyncio.sleep(0.2)
                            await page.keyboard.press('Control+a')
                            await asyncio.sleep(0.1)
                            await page.keyboard.press('Delete')
                            await asyncio.sleep(random.uniform(0.3, 0.8))
                            logger.info(f"[{index}] ✅ Input field cleared, ready for next number")
                        except Exception as e:
                            logger.error(f"[{index}] ⚠️ Error clearing field after registered_continue: {e}")
                            # Fall back to going back if field clearing fails
                            if not await go_back_and_retry(page, index):
                                logger.error(f"[{index}] ❌ Failed to go back after field clearing error, will restart instance")
                                break
                    
                    elif status == 'registered':
                        # Number already saved and removed in check_registration_status
                        # Go back and try another number (fallback for when 6th button click fails)
                        if not await go_back_and_retry(page, index):
                            logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                            break
                            
                    elif status == 'not_registered':
                        # Number already saved and removed in check_registration_status
                        # Go back and try another number
                        if not await go_back_and_retry(page, index):
                            logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                            break
                            
                    elif status == 'error':
                        # Something went wrong, try to go back and retry same number
                        logger.warning(f"[{index}] ⚠️ Unclear status, trying to go back and retry...")
                        if not await go_back_and_retry(page, index):
                            logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                            break
                    
                    # Small delay between attempts
                    await asyncio.sleep(random.uniform(1, 3))

                # Check final result
                if cookie_found:
                    logger.info(f"[{index}] ✅ Successfully obtained cookie after {attempt} attempts")
                else:
                    logger.warning(f"[{index}] ❌ No cookie found after {max_attempts} attempts, restarting instance")

                await browser.close()
                logger.debug(f"[{index}] Browser instance closed")
                
                # Random delay before next iteration
                next_delay = random.uniform(3, 8)
                logger.info(f"[{index}] Waiting {next_delay:.1f}s before next attempt...")
                await asyncio.sleep(next_delay)
                
        except Exception as e:
            logger.error(f"[{index}] ❌ Error: {e}")
            # Random cooldown on error
            error_delay = random.uniform(5, 12)
            logger.info(f"[{index}] Error cooldown: {error_delay:.1f}s")
            await asyncio.sleep(error_delay)

async def cleanup_result_files():
    """Remove duplicate entries from result files at startup"""
    global _processed_numbers
    
    with _file_lock:
        try:
            # Clean registered.txt
            if os.path.exists("results/registered.txt"):
                with open("results/registered.txt", "r", encoding='utf-8') as f:
                    registered_numbers = [line.strip() for line in f if line.strip()]
                
                # Remove duplicates while preserving order
                unique_registered = []
                seen = set()
                for num in registered_numbers:
                    if num not in seen:
                        unique_registered.append(num)
                        seen.add(num)
                        _processed_numbers.add(num)  # Mark as processed
                
                if len(unique_registered) != len(registered_numbers):
                    with open("results/registered.txt", "w", encoding='utf-8') as f:
                        if unique_registered:
                            f.write("\n".join(unique_registered) + "\n")
                    logger.info(f"Cleaned registered.txt: {len(registered_numbers)} -> {len(unique_registered)} (removed {len(registered_numbers) - len(unique_registered)} duplicates)")
                else:
                    for num in unique_registered:
                        _processed_numbers.add(num)
            
            # Clean not_registered.txt
            if os.path.exists("results/not_registered.txt"):
                with open("results/not_registered.txt", "r", encoding='utf-8') as f:
                    not_registered_numbers = [line.strip() for line in f if line.strip()]
                
                # Remove duplicates while preserving order
                unique_not_registered = []
                seen = set()
                for num in not_registered_numbers:
                    if num not in seen:
                        unique_not_registered.append(num)
                        seen.add(num)
                        _processed_numbers.add(num)  # Mark as processed
                
                if len(unique_not_registered) != len(not_registered_numbers):
                    with open("results/not_registered.txt", "w", encoding='utf-8') as f:
                        if unique_not_registered:
                            f.write("\n".join(unique_not_registered) + "\n")
                    logger.info(f"Cleaned not_registered.txt: {len(not_registered_numbers)} -> {len(unique_not_registered)} (removed {len(not_registered_numbers) - len(unique_not_registered)} duplicates)")
                else:
                    for num in unique_not_registered:
                        _processed_numbers.add(num)
                        
            logger.info(f"Cleanup completed. {len(_processed_numbers)} numbers marked as already processed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    # Clean up duplicates before starting
    logger.info("🧹 Cleaning up duplicate entries from previous runs...")
    await cleanup_result_files()
    
    # Start with fewer instances to prevent race conditions
    logger.info("🚀 Starting browser fingerprint rotation system...")
    logger.info("📊 Each request will use a completely different fingerprint")
    logger.info(f"Starting {5} browser instances (reduced to prevent race conditions)")
    tasks = [run_instance(i) for i in range(5)]  # Reduced from 20 to 5 instances
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())