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

async def check_registration_status(page, phone_number, index, browser=None):
    """
    Check if phone number is registered by looking for specific text patterns
    Returns: 'registered', 'not_registered', 'cookie_found', or 'error'
    """
    try:
        # Wait a bit after clicking Weiter and ensure page is stable
        logger.info(f"[{index}] ⏳ Waiting for page response after clicking Weiter...")
        await asyncio.sleep(random.uniform(2, 4))
        
        # Check if page is still loading and wait for completion
        loading_complete = False
        for stability_check in range(15):  # Check for up to 15 seconds
            try:
                # Check document ready state
                ready_state = await page.evaluate("document.readyState")
                
                # Check for active loading indicators
                loading_indicators = await page.query_selector_all('.loading, .spinner, [data-loading="true"], .progress, .loader')
                
                if ready_state == "complete" and len(loading_indicators) == 0:
                    logger.info(f"[{index}] ✅ Page fully loaded and stable after Weiter click")
                    loading_complete = True
                    break
                else:
                    logger.debug(f"[{index}] ⏳ Page still loading (ready: {ready_state}, loaders: {len(loading_indicators)})")
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.warning(f"[{index}] ⚠️ Error checking page stability: {e}")
                await asyncio.sleep(1)
        
        if not loading_complete:
            logger.warning(f"[{index}] ⚠️ Page may still be loading after 15 seconds, proceeding anyway...")
        
        # Additional wait for any animations or transitions
        await asyncio.sleep(random.uniform(1, 2))
        
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
                                logger.info(f"[{index}] ⏳ Waiting 2-3 seconds for page to stabilize...")
                                await asyncio.sleep(random.uniform(2, 3))
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
                                                    logger.info(f"[{index}] ⏳ Waiting 2-3 seconds for page to stabilize...")
                                                    await asyncio.sleep(random.uniform(2, 3))
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
                                    logger.info(f"[{index}] ⏳ Waiting 2-3 seconds for page to stabilize...")
                                    await asyncio.sleep(random.uniform(2, 3))
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
                    
                    # Wait for popup or page changes after progress completion
                    logger.info(f"[{index}] ⏳ Waiting for popup or page changes after progress completion...")
                    await asyncio.sleep(2)  # Initial wait
                    
                    # Check for popup or page state changes
                    popup_or_change_detected = False
                    for check_attempt in range(10):  # Check for up to 5 seconds
                        try:
                            # Check for various popup indicators
                            popup_selectors = [
                                '[role="dialog"]',
                                '.modal',
                                '.popup',
                                'text=Wir haben ein existierendes Konto gefunden',
                                'text=existierendes Konto',
                                'text=Konto gefunden',
                                'text=Wie heißen Sie?',
                                'input[placeholder*="Vorname"]',
                                'input[placeholder*="Nachname"]',
                                'text=Vorname',
                                'text=Nachname'
                            ]
                            
                            for selector in popup_selectors:
                                try:
                                    element = await page.wait_for_selector(selector, timeout=500)
                                    if element:
                                        logger.info(f"[{index}] 🎯 Popup/page change detected: {selector}")
                                        popup_or_change_detected = True
                                        break
                                except:
                                    continue
                            
                            if popup_or_change_detected:
                                break
                                
                            # Check if URL changed
                            current_url = page.url
                            if "registrations" not in current_url:
                                logger.info(f"[{index}] 🔄 Page change detected - URL changed to: {current_url}")
                                popup_or_change_detected = True
                                break
                            
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            logger.debug(f"[{index}] Check attempt {check_attempt + 1}: {e}")
                            await asyncio.sleep(0.5)
                    
                    if popup_or_change_detected:
                        logger.info(f"[{index}] ✅ Popup or page change confirmed, proceeding with cookie extraction...")
                    else:
                        logger.info(f"[{index}] ⚠️ No popup/page change detected, but proceeding with cookie extraction...")
                    
                    # Additional wait for stability after popup/change detection
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # Check for cookies after progress completion and popup/page change
                    cookies = await page.context.cookies()
                    dl_frcid = next((c['value'] for c in cookies if c['name'] == 'dl_frcid'), None)
                    if dl_frcid:
                        logger.info(f"[{index}] 🍪 Cookie found after progress completion and popup/page change: {dl_frcid}")
                        
                        # Save cookie to file
                        with open("cookies.txt", "a") as f:
                            f.write(f"{dl_frcid}\n")
                        logger.info(f"[{index}] 💾 Cookie saved to cookies.txt: {dl_frcid}")
                        
                        # DON'T close browser - continue processing more phone numbers
                        logger.info(f"[{index}] � Cookie saved, continuing to process more phone numbers...")
                        
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
        
        # Check for "Wie heißen Sie?" text (indicates not registered - click "Andere Telefonnummer nutzen" to continue)
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
                        logger.info(f"[{index}] ❌ Phone {phone_number} - NOT REGISTERED (found '{selector}') - saving and continuing search for progress bar")
                        # Save to not_registered.txt and remove from phone_numbers.txt
                        save_phone_result(phone_number, False)
                        remove_phone_from_file(phone_number)
                        
                        # Click "Andere Telefonnummer nutzen" to continue searching for progress bar
                        try:
                            andere_button = await page.wait_for_selector('text=Andere Telefonnummer nutzen', timeout=5000)
                            if andere_button:
                                await andere_button.click()
                                await asyncio.sleep(random.uniform(1, 2))
                                logger.info(f"[{index}] ✅ Clicked 'Andere Telefonnummer nutzen' - continuing search for progress bar")
                                return 'not_registered_continue'  # New status to continue without going back
                            else:
                                logger.warning(f"[{index}] ⚠️ 'Andere Telefonnummer nutzen' button not found, going back normally")
                                return 'not_registered'
                        except Exception as e:
                            logger.error(f"[{index}] ❌ Error clicking 'Andere Telefonnummer nutzen': {e}")
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
                            logger.info(f"[{index}] ✅ Phone {phone_number} - REGISTERED (found existing account) - saving and going back to continue search for progress bar")
                            # Save to registered.txt and remove from phone_numbers.txt
                            save_phone_result(phone_number, True)
                            remove_phone_from_file(phone_number)
                            
                            # Go back to continue searching for progress bar instead of trying to continue
                            logger.info(f"[{index}] ⬅️ Going back to continue search for progress bar...")
                            return 'registered'  # Go back and try next number
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
        
        # Wait for page to load after going back
        logger.info(f"[{index}] ⏳ Waiting for page to load after going back...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            logger.debug(f"[{index}] Page loaded successfully after going back")
        except Exception as e:
            logger.warning(f"[{index}] ⚠️ Network idle timeout after going back: {e}")
        
        await asyncio.sleep(random.uniform(1, 2))
        
        # Wait for the input field and ensure it's ready
        input_selector = '.oxygen-input-field__input.text-ellipsis'
        logger.info(f"[{index}] 🎯 Waiting for input field after going back...")
        
        # Wait for field with retries
        field_ready = False
        for retry in range(3):
            try:
                await page.wait_for_selector(input_selector, timeout=10000)
                
                # Check if field is interactive
                field_element = await page.query_selector(input_selector)
                if field_element:
                    is_enabled = await field_element.is_enabled()
                    is_visible = await field_element.is_visible()
                    
                    if is_enabled and is_visible:
                        field_ready = True
                        break
                    else:
                        logger.warning(f"[{index}] ⚠️ Field not ready (enabled: {is_enabled}, visible: {is_visible}), retrying...")
                        await asyncio.sleep(2)
            except Exception as e:
                logger.warning(f"[{index}] ⚠️ Field wait attempt {retry + 1} failed: {e}")
                if retry < 2:
                    await asyncio.sleep(2)
        
        if not field_ready:
            logger.error(f"[{index}] ❌ Input field not ready after going back")
            return False
        
        # Multiple methods to ensure field is cleared
        await page.click(input_selector)  # Focus the field
        await asyncio.sleep(0.2)
        await page.keyboard.press('Control+a')  # Select all text
        await asyncio.sleep(0.1)
        await page.keyboard.press('Delete')  # Delete selected text
        await asyncio.sleep(random.uniform(0.5, 1))
        
        logger.debug(f"[{index}] ✅ Successfully went back and cleared input field")
        return True
    except Exception as e:
        logger.error(f"[{index}] ❌ Error going back: {e}")
        return False

def get_next_phone_number():
    """Get the next phone number from results/phone_numbers.txt (thread-safe)"""
    global _processed_numbers
    
    with _file_lock:
        try:
            phone_file_path = "results/phone_numbers.txt"
            
            # Debug: Check if file exists and get its absolute path
            abs_path = os.path.abspath(phone_file_path)
            logger.debug(f"Looking for phone numbers file at: {abs_path}")
            logger.debug(f"File exists: {os.path.exists(phone_file_path)}")
            
            if not os.path.exists(phone_file_path):
                logger.warning(f"Phone numbers file not found: {phone_file_path}")
                logger.warning(f"Absolute path checked: {abs_path}")
                return None
                
            with open(phone_file_path, "r", encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            logger.debug(f"Total lines read from file: {len(lines)}")
            logger.debug(f"Already processed numbers: {len(_processed_numbers)}")
            
            if not lines:
                logger.warning(f"No phone numbers available in {phone_file_path}")
                return None
                
            # Find first number that hasn't been processed yet
            available_numbers = []
            processed_numbers = []
            
            for phone_number in lines:
                if phone_number not in _processed_numbers:
                    available_numbers.append(phone_number)
                else:
                    processed_numbers.append(phone_number)
            
            logger.debug(f"Available numbers (not processed): {len(available_numbers)}")
            logger.debug(f"Already processed numbers: {len(processed_numbers)}")
            
            if available_numbers:
                selected_number = available_numbers[0]
                _processed_numbers.add(selected_number)
                logger.info(f"Retrieved next phone number: {selected_number} (Available: {len(available_numbers)-1}, Total processed: {len(_processed_numbers)})")
                return selected_number
            
            logger.warning("All phone numbers in file have been processed")
            logger.info(f"Total numbers in file: {len(lines)}, All processed: {len(_processed_numbers)}")
            # Reset processed numbers to start over
            logger.info("🔄 Resetting processed numbers to start over...")
            _processed_numbers.clear()
            
            if lines:
                selected_number = lines[0]
                _processed_numbers.add(selected_number)
                logger.info(f"After reset - Retrieved phone number: {selected_number}")
                return selected_number
            return None
        except Exception as e:
            logger.error(f"Error reading phone numbers: {e}")
            return None

def clear_processed_numbers():
    """Clear the processed numbers set to start fresh"""
    global _processed_numbers
    with _file_lock:
        _processed_numbers.clear()
        logger.info("🔄 Processed numbers cleared manually")

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
    logger.info(f"[{index}] 🎯 MAIN MISSION: Find phone numbers that trigger PROGRESS BAR to get COOKIES!")
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
                
                # Enhanced page loading with multiple wait conditions
                logger.info(f"[{index}] 🌐 Loading page and waiting for full initialization...")
                await page.goto(URL, wait_until="networkidle", timeout=60000)  # Increased timeout
                
                # Wait for initial page stabilization
                await asyncio.sleep(random.uniform(2, 4))
                
                # Check if page is still loading and wait for completion
                logger.info(f"[{index}] ⏳ Checking page loading state...")
                for loading_check in range(10):  # Check for up to 10 seconds
                    try:
                        # Check document ready state
                        ready_state = await page.evaluate("document.readyState")
                        logger.debug(f"[{index}] Document ready state: {ready_state}")
                        
                        if ready_state == "complete":
                            logger.info(f"[{index}] ✅ Document fully loaded")
                            break
                        else:
                            logger.info(f"[{index}] ⏳ Document still loading ({ready_state}), waiting...")
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"[{index}] ⚠️ Error checking ready state: {e}")
                        await asyncio.sleep(1)
                
                # Additional wait for any dynamic content
                logger.info(f"[{index}] 🔄 Waiting for dynamic content to load...")
                await asyncio.sleep(random.uniform(1, 3))
                
                # Check for loading indicators and wait for them to disappear
                loading_indicators = [
                    '.loading',
                    '.spinner',
                    '[data-loading="true"]',
                    '.progress',
                    '.loader'
                ]
                
                for indicator in loading_indicators:
                    try:
                        loading_element = await page.wait_for_selector(indicator, timeout=2000)
                        if loading_element:
                            logger.info(f"[{index}] ⏳ Found loading indicator: {indicator}, waiting for completion...")
                            # Wait for loading indicator to disappear
                            await page.wait_for_selector(indicator, state="detached", timeout=30000)
                            logger.info(f"[{index}] ✅ Loading indicator disappeared: {indicator}")
                    except:
                        continue  # No loading indicator found or already gone
                
                # Wait for the main input field with extended timeout and retries
                logger.info(f"[{index}] 🎯 Waiting for input field to be available...")
                input_field_ready = False
                for field_check in range(5):  # Try up to 5 times
                    try:
                        await page.wait_for_selector('.oxygen-input-field__input.text-ellipsis', timeout=15000)
                        
                        # Additional check to ensure field is interactive
                        field_element = await page.query_selector('.oxygen-input-field__input.text-ellipsis')
                        if field_element:
                            is_enabled = await field_element.is_enabled()
                            is_visible = await field_element.is_visible()
                            
                            if is_enabled and is_visible:
                                logger.info(f"[{index}] ✅ Input field is ready and interactive")
                                input_field_ready = True
                                break
                            else:
                                logger.warning(f"[{index}] ⚠️ Input field found but not ready (enabled: {is_enabled}, visible: {is_visible})")
                                await asyncio.sleep(2)
                        else:
                            logger.warning(f"[{index}] ⚠️ Input field element not found, retrying...")
                            await asyncio.sleep(2)
                    except Exception as e:
                        logger.warning(f"[{index}] ⚠️ Input field check attempt {field_check + 1} failed: {e}")
                        if field_check < 4:  # If not the last attempt
                            await asyncio.sleep(3)
                        else:
                            logger.error(f"[{index}] ❌ Failed to find input field after 5 attempts")
                            raise
                
                if not input_field_ready:
                    logger.error(f"[{index}] ❌ Input field never became ready, cannot proceed")
                    raise Exception("Input field not ready after multiple attempts")
                
                logger.debug(f"[{index}] ✅ Page fully loaded and input field ready")
                
                # Add random delay to mimic human behavior after page load
                await asyncio.sleep(random.uniform(1, 3))
                
                # Main loop for testing phone numbers - continue until no more numbers
                while True:  # Continue indefinitely until no more phone numbers
                    
                    # Get next phone number from file
                    phone_number = get_next_phone_number()
                    if not phone_number:
                        logger.warning(f"[{index}] 📱 No more phone numbers available in file")
                        break
                    
                    # Process this phone number with retry logic
                    max_attempts_per_number = 3  # Maximum attempts per individual phone number
                    phone_processed = False
                    
                    for attempt in range(1, max_attempts_per_number + 1):
                        logger.info(f"[{index}] 🔍 SEARCHING FOR PROGRESS BAR - Attempt {attempt}/{max_attempts_per_number} - Testing phone: {phone_number}")
                    
                        # Add random delay before typing
                        await asyncio.sleep(random.uniform(3, 5))
                        
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
                        
                        # Check registration status with protection against page loading
                        logger.info(f"[{index}] 🔍 Checking registration status for {phone_number}...")
                        
                        # Ensure page is stable before checking status
                        try:
                            # Wait for any loading to complete
                            await page.wait_for_load_state("networkidle", timeout=10000)
                            logger.debug(f"[{index}] Page network idle confirmed")
                        except Exception as e:
                            logger.warning(f"[{index}] ⚠️ Network idle wait timeout: {e}")
                        
                        # Additional stability check
                        await asyncio.sleep(1)
                        
                        status = await check_registration_status(page, phone_number, index, browser)
                        logger.info(f"[{index}] Registration status for {phone_number}: {status}")
                        
                        if status == 'cookie_found':
                            # MAIN MISSION ACCOMPLISHED! Cookie saved - close browser and start fresh
                            logger.info(f"[{index}] 🎉 MAIN MISSION SUCCESS! Cookie saved, closing browser and starting new instance...")
                            phone_processed = True
                            
                            # Close current browser instance
                            logger.info(f"[{index}] 🔄 Closing browser instance after cookie found...")
                            try:
                                await browser.close()
                                logger.info(f"[{index}] ✅ Browser closed successfully after cookie found")
                            except Exception as e:
                                logger.warning(f"[{index}] ⚠️ Error closing browser: {e}")
                            
                            # Break out of both loops to restart with new instance
                            raise Exception("COOKIE_FOUND_RESTART")  # Special exception to restart instance
                        
                        elif status == 'not_registered_continue':
                            # Number saved as not registered, "Andere Telefonnummer nutzen" clicked
                            # Continue with same page to try next number (no need to go back)
                            logger.info(f"[{index}] 🔄 Not registered number handled, input field ready for next number...")
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
                                logger.info(f"[{index}] ✅ Input field cleared, continuing search for progress bar...")
                                phone_processed = True
                                break  # Exit attempt loop for this phone, move to next phone
                            except Exception as e:
                                logger.error(f"[{index}] ⚠️ Error clearing field after not_registered_continue: {e}")
                                # Fall back to going back if field clearing fails
                                if not await go_back_and_retry(page, index):
                                    logger.error(f"[{index}] ❌ Failed to go back after field clearing error, will restart instance")
                                    phone_processed = True  # Mark as processed to avoid infinite retry
                                    break
                        
                        elif status == 'registered_continue':
                            # This status is no longer used, but keeping for compatibility
                            logger.info(f"[{index}] 🔄 Registered number handled, going back to continue search...")
                            if not await go_back_and_retry(page, index):
                                logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                                phone_processed = True  # Mark as processed to avoid infinite retry
                                break
                            phone_processed = True
                            break  # Exit attempt loop for this phone, move to next phone
                        
                        elif status == 'registered':
                            # Number already saved as registered, go back and continue searching for progress bar
                            logger.info(f"[{index}] ⬅️ Registered number saved, going back to continue search for progress bar...")
                            if not await go_back_and_retry(page, index):
                                logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                                phone_processed = True  # Mark as processed to avoid infinite retry
                                break
                            phone_processed = True
                            break  # Exit attempt loop for this phone, move to next phone
                                
                        elif status == 'not_registered':
                            # Number already saved as not registered, go back and continue searching for progress bar
                            logger.info(f"[{index}] ⬅️ Not registered number saved, going back to continue search for progress bar...")
                            if not await go_back_and_retry(page, index):
                                logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                                phone_processed = True  # Mark as processed to avoid infinite retry
                                break
                            phone_processed = True
                            break  # Exit attempt loop for this phone, move to next phone
                                
                        elif status == 'error':
                            # Something went wrong, try to go back and retry same number
                            logger.warning(f"[{index}] ⚠️ Unclear status, trying to go back and retry...")
                            if not await go_back_and_retry(page, index):
                                logger.error(f"[{index}] ❌ Failed to go back, will restart instance")
                                phone_processed = True  # Mark as processed to avoid infinite retry
                                break
                            # Continue to next attempt for same phone number
                        
                        # Small delay between attempts if retrying
                        if attempt < max_attempts_per_number:
                            await asyncio.sleep(random.uniform(4, 6))
                    
                    # If phone wasn't processed successfully after all attempts, log it
                    if not phone_processed:
                        logger.warning(f"[{index}] ⚠️ Failed to process {phone_number} after {max_attempts_per_number} attempts")

                # Check final result - just log the completion
                logger.info(f"[{index}] ✅ Browser instance completed processing available numbers")
                
                # Ensure no ongoing operations before closing browser
                logger.info(f"[{index}] 🔄 Ensuring all operations are complete before closing browser...")
                try:
                    # Wait for any final network activity to complete
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    logger.debug(f"[{index}] Final network idle confirmed")
                except:
                    logger.debug(f"[{index}] Network idle timeout, proceeding with closure")
                
                # Brief wait before closing
                await asyncio.sleep(2)

                await browser.close()
                logger.debug(f"[{index}] Browser instance closed safely")
                
                # Random delay before next iteration
                next_delay = random.uniform(3, 8)
                logger.info(f"[{index}] Waiting {next_delay:.1f}s before next attempt...")
                await asyncio.sleep(next_delay)
                
        except Exception as e:
            # Check if this is our special restart exception
            if str(e) == "COOKIE_FOUND_RESTART":
                logger.info(f"[{index}] 🔄 Restarting instance with new browser after cookie found...")
                # Random delay before restarting
                restart_delay = random.uniform(2, 5)
                logger.info(f"[{index}] Waiting {restart_delay:.1f}s before restarting instance...")
                await asyncio.sleep(restart_delay)
                continue  # Continue to next iteration to start new browser instance
            
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
    logger.info(f"Starting {7} browser instances (reduced to prevent race conditions)")
    tasks = [run_instance(i) for i in range(7)]  # Reduced from 20 to 7 instances
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())