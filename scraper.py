
import asyncio
import random,sys
import logging
import threading
import os
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# File operation lock to prevent race conditions
file_lock = threading.Lock()

# Track failed phone numbers for retry
failed_numbers = {}  # phone_number -> retry_count

print(f"Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Scraper started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def safe_remove_phone_number(phone_number):
    """Safely remove a phone number from the file with proper locking and error handling."""
    try:
        with file_lock:
            # Read current file
            if not os.path.exists("results/phone_numbers.txt"):
                logger.warning("phone_numbers.txt does not exist during removal")
                return False
            
            with open("results/phone_numbers.txt", "r", encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # Check if phone number exists
            if phone_number not in lines:
                logger.debug(f"Phone number {phone_number} not found in file (already removed?)")
                return False
            
            # Remove the phone number
            lines.remove(phone_number)
            
            # Write back to file
            with open("results/phone_numbers.txt", "w", encoding='utf-8') as f:
                if lines:
                    f.write("\n".join(lines) + "\n")
                else:
                    f.write("")  # Empty file
            
            logger.debug(f"Successfully removed {phone_number}. Remaining: {len(lines)}")
            return True
            
    except Exception as e:
        logger.error(f"Error removing phone number {phone_number}: {e}")
        return False

def safe_read_phone_numbers():
    """Safely read phone numbers from file with proper error handling."""
    try:
        with file_lock:
            if not os.path.exists("results/phone_numbers.txt"):
                return []
            
            with open("results/phone_numbers.txt", "r", encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            return lines
    except Exception as e:
        logger.error(f"Error reading phone numbers: {e}")
        return []

def add_number_for_retry(phone_number, max_retries=3):
    """Add a failed phone number back to the file for retry if under retry limit."""
    global failed_numbers
    
    retry_count = failed_numbers.get(phone_number, 0) + 1
    failed_numbers[phone_number] = retry_count
    
    if retry_count <= max_retries:
        try:
            with file_lock:
                # Add back to phone_numbers.txt for retry
                with open("results/phone_numbers.txt", "a", encoding='utf-8') as f:
                    f.write(f"{phone_number}\n")
                logger.info(f"Added {phone_number} for retry {retry_count}/{max_retries}")
                return True
        except Exception as e:
            logger.error(f"Error adding {phone_number} for retry: {e}")
    else:
        logger.warning(f"Phone number {phone_number} exceeded max retries ({max_retries}), giving up")
        # Write to not_registered as final fallback
        try:
            with open("results/not_registered.txt", "a", encoding='utf-8') as f:
                f.write(f"{phone_number}\n")
        except Exception as e:
            logger.error(f"Error writing {phone_number} to not_registered.txt: {e}")
    
    return False

async def check_phone_number(session, phone_number, cookie, proxy, headers_template, url):
    headers = headers_template.copy()
    headers["cookie"] = f"dl_frcid={cookie}"
    payload = {"username": phone_number, "clientId": "patient-de-client"}

    try:
        logger.debug(f"Checking phone number: {phone_number} with cookie: {cookie[:8]}...")
        async with session.post(url, json=payload, headers=headers, proxy=proxy, timeout=15) as response:
            if response.status == 200:
                data = await response.json()
                result = "registered" if data.get("account_exists") else "not_registered"
                logger.info(f"[OK] {phone_number} -> {result}")
                print(f"[OK] {phone_number} -> {result}")
                
                # Write to appropriate result file
                result_file = "results/registered.txt" if data.get("account_exists") else "results/not_registered.txt"
                try:
                    with open(result_file, "a", encoding='utf-8') as f:
                        f.write(f"{phone_number}\n")
                except Exception as e:
                    logger.error(f"Error writing to {result_file}: {e}")
                
                # Remove from phone_numbers.txt
                safe_remove_phone_number(phone_number)
                
                return "success", cookie, phone_number
            elif response.status == 401:
                logger.warning(f"[COOKIE_INVALID] {phone_number} - Cookie {cookie[:8]}... returned 401 (Unauthorized)")
                print(f"[COOKIE_INVALID] {phone_number} - Cookie expired/invalid")
                
                # Return cookie as invalid for retry with different cookie
                return "invalid_cookie_retry", cookie, phone_number
            else:
                logger.warning(f"[ERROR] {phone_number} failed. Status: {response.status}")
                print(f"[ERROR] {phone_number} failed. Status: {response.status}")
                response_text = await response.text()
                logger.warning(f"Response: {response_text}")
                print(f"Response: {response_text}")
                
                # Write to not_registered file for failed requests
                try:
                    with open("results/not_registered.txt", "a", encoding='utf-8') as f:
                        f.write(f"{phone_number}\n")
                except Exception as e:
                    logger.error(f"Error writing to not_registered.txt: {e}")
                
                # Remove from phone_numbers.txt
                safe_remove_phone_number(phone_number)
                
                # Return as invalid_cookie_no_retry so cookie gets removed but number doesn't get retried
                return "invalid_cookie_no_retry", cookie, phone_number
    except asyncio.TimeoutError:
        logger.error(f"[TIMEOUT] {phone_number} with cookie {cookie[:8]}... timed out")
        print(f"[TIMEOUT] {phone_number} with cookie failed: timeout")
        
        # Don't remove from phone_numbers.txt on timeout - retry later
        return "timeout", cookie, phone_number
    except Exception as e:
        error_msg = str(e)
        if "10054" in error_msg or "forcibly closed" in error_msg:
            logger.error(f"[CONNECTION_CLOSED] {phone_number} - Remote host closed connection")
            print(f"[CONNECTION_CLOSED] {phone_number} - Connection forcibly closed")
            # Don't remove from phone_numbers.txt - this is likely rate limiting
            return "connection_closed", cookie, phone_number
        else:
            logger.error(f"[EXCEPTION] {phone_number} with cookie {cookie[:8]}... failed: {e}")
            print(f"[EXCEPTION] {phone_number} with cookie failed: {e}")
            
            # Remove from phone_numbers.txt for other exceptions
            safe_remove_phone_number(phone_number)
            
            return "exception", cookie, phone_number

async def remove_cookie(cookie, cookie_list, cookie_usage, cookie_limits):
    logger.info(f"Removing cookie {cookie[:8]}... (limit reached)")
    print(f"[INFO] Removing cookie {cookie[:8]}... (limit reached)")
    if cookie in cookie_list:
        cookie_list.remove(cookie)
    if cookie in cookie_usage:
        del cookie_usage[cookie]
    if cookie in cookie_limits:
        del cookie_limits[cookie]
    with open("cookies.txt", "w") as f:
        f.write("\n".join(cookie_list) + "\n")
    logger.info(f"Cookie removed. Remaining cookies: {len(cookie_list)}")

async def remove_invalid_cookie(cookie, cookie_list, cookie_usage, cookie_limits):
    """Remove invalid/expired cookie from all tracking"""
    logger.warning(f"Removing invalid cookie {cookie[:8]}... (non-200 response)")
    print(f"[INFO] Removing invalid cookie {cookie[:8]}... (non-200 response)")
    if cookie in cookie_list:
        cookie_list.remove(cookie)
    if cookie in cookie_usage:
        del cookie_usage[cookie]
    if cookie in cookie_limits:
        del cookie_limits[cookie]
    # Update cookies.txt file
    with open("cookies.txt", "w") as f:
        f.write("\n".join(cookie_list) + "\n")
    logger.warning(f"Invalid cookie removed. Remaining cookies: {len(cookie_list)}")

async def load_cookies():
    try:
        with open("cookies.txt", "r") as f:
            cookies = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(cookies)} cookies from file")
            return cookies
    except FileNotFoundError:
        logger.warning("cookies.txt file not found")
        return []

async def scraping():
    url = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/accounts/check_existence"

    # Load phone numbers initially
    phone_numbers = safe_read_phone_numbers()
    if not phone_numbers:
        logger.error("No phone numbers found in phone_numbers.txt")
        return
    
    logger.info(f"Loaded {len(phone_numbers)} phone numbers to process")

    cookies = await load_cookies()
    if not cookies:
        logger.warning("No cookies found in cookies.txt. Waiting for 60 seconds.")
        print("[INFO] No cookies found in cookies.txt. Waiting for 60 seconds.")
        await asyncio.sleep(60)
        cookies = await load_cookies()
        if not cookies:
            logger.error("Still no cookies found. Exiting.")
            print("[ERROR] Still no cookies found. Exiting.")
            return

    cookie_limits = {cookie: random.randint(5, 7) for cookie in cookies}
    cookie_usage = {cookie: 0 for cookie in cookies}
    cookie_list = list(cookies)
    
    logger.info(f"Initialized {len(cookie_list)} cookies with limits: {[cookie_limits[c] for c in cookie_list[:5]]}...")

    # Build proxy URL from individual components
    proxy_server = os.getenv("PROXY_SERVER")
    proxy_username = os.getenv("PROXY_USERNAME")
    proxy_password = os.getenv("PROXY_PASSWORD")
    
    if all([proxy_server, proxy_username, proxy_password]):
        # Remove http:// from server if present to avoid double protocol
        server_clean = proxy_server.replace("http://", "").replace("https://", "")
        proxy = f"http://{proxy_username}:{proxy_password}@{server_clean}"
        logger.info(f"Built proxy URL from components: {proxy[:30]}...")
    else:
        logger.warning("Proxy configuration not found in environment variables. Running without proxy.")
        proxy = None

    headers_template = {
        "host": "www.doctolib.de",
        "connection": "keep-alive",
        "sec-ch-ua-platform": "\"Windows\"",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "accept": "application/json, text/plain, */*",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
        "content-type": "application/json",
        "sec-ch-ua-mobile": "?0",
        "origin": "https://www.doctolib.de",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9"
    }

    # Create session with better connection handling
    timeout = ClientTimeout(total=20, connect=10)
    connector = TCPConnector(
        limit=10,  # Total connection pool size
        limit_per_host=5,  # Max connections per host
        ttl_dns_cache=300,  # DNS cache TTL
        use_dns_cache=True,
        keepalive_timeout=60,
        enable_cleanup_closed=True
    )

    async with ClientSession(timeout=timeout, connector=connector) as session:
        processed_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 50  # Stop if too many consecutive errors
        
        # Process phone numbers in batches until file is empty
        while True:
            # Get current phone numbers from file (in case it was updated)
            current_numbers = safe_read_phone_numbers()
            
            if not current_numbers:
                logger.info("No more phone numbers to process. File is empty.")
                break
            
            # Check if we have too many consecutive errors
            if consecutive_errors >= max_consecutive_errors:
                logger.error(f"Too many consecutive errors ({consecutive_errors}). Pausing for 5 minutes.")
                print(f"[ERROR] Too many consecutive errors. Pausing for 5 minutes.")
                await asyncio.sleep(300)  # 5 minutes
                consecutive_errors = 0
                continue
            
            logger.info(f"Processing batch with {len(current_numbers)} remaining numbers")
            
            # Take up to 5 numbers for this batch (reduced from 10 to avoid overwhelming)
            batch_size = min(5, len(current_numbers))
            batch_numbers = current_numbers[:batch_size]
            
            logger.info(f"Processing batch of {batch_size} numbers")
            
            tasks = []
            cookie_index = 0
            
            for phone_number in batch_numbers:
                # Check if we have cookies available
                if not cookie_list:
                    logger.warning("No cookies left. Waiting for 60 seconds.")
                    print("[INFO] No cookies left. Waiting for 60 seconds.")
                    await asyncio.sleep(60)
                    new_cookies = await load_cookies()
                    if not new_cookies:
                        logger.error("No cookies available after waiting. Exiting.")
                        print("[ERROR] No cookies available after waiting. Exiting.")
                        return
                    cookie_list.extend(new_cookies)
                    for cookie in new_cookies:
                        cookie_usage[cookie] = 0
                        cookie_limits[cookie] = random.randint(5, 7)
                    logger.info(f"Added {len(new_cookies)} new cookies")

                current_cookie = cookie_list[cookie_index % len(cookie_list)]
                logger.debug(f"Using cookie {current_cookie[:8]}... for {phone_number}")
                tasks.append(check_phone_number(session, phone_number, current_cookie, proxy, headers_template, url))
                cookie_index += 1

            # Process the batch
            if tasks:
                logger.info(f"Executing batch of {len(tasks)} tasks")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                batch_success_count = 0
                invalid_cookies = set()
                
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {idx} failed with exception: {result}")
                        consecutive_errors += 1
                        continue
                    if result is None:
                        logger.warning(f"Task {idx} returned None")
                        consecutive_errors += 1
                        continue
                    
                    result_type, cookie, phone_number = result
                    
                    if result_type == "success":
                        processed_count += 1
                        batch_success_count += 1
                        consecutive_errors = 0  # Reset on success
                        
                        # Update cookie usage
                        if cookie in cookie_usage:
                            cookie_usage[cookie] += 1
                            logger.debug(f"Cookie {cookie[:8]}... usage: {cookie_usage[cookie]}/{cookie_limits[cookie]}")
                            
                            if cookie_usage[cookie] >= cookie_limits[cookie]:
                                await remove_cookie(cookie, cookie_list, cookie_usage, cookie_limits)
                    
                    elif result_type == "invalid_cookie_retry":
                        logger.warning(f"Cookie {cookie[:8]}... is invalid (401), marking for removal")
                        invalid_cookies.add(cookie)
                        # Add the phone number back for retry with a different cookie
                        if add_number_for_retry(phone_number):
                            logger.info(f"Added {phone_number} back for retry with different cookie")
                        consecutive_errors += 1
                    
                    elif result_type == "invalid_cookie_no_retry":
                        logger.warning(f"Cookie {cookie[:8]}... is invalid (HTTP error), marking for removal")
                        invalid_cookies.add(cookie)
                        processed_count += 1  # Count as processed since we won't retry
                        consecutive_errors += 1
                    
                    elif result_type in ["timeout", "connection_closed"]:
                        logger.warning(f"Network issue with {phone_number}: {result_type}")
                        # Add back for retry
                        if add_number_for_retry(phone_number):
                            logger.info(f"Added {phone_number} back for retry due to {result_type}")
                        consecutive_errors += 1
                    
                    else:  # exception
                        consecutive_errors += 1
                
                # Remove all invalid cookies
                for invalid_cookie in invalid_cookies:
                    await remove_invalid_cookie(invalid_cookie, cookie_list, cookie_usage, cookie_limits)
                
                # Check if we need to reload cookies
                if not cookie_list:
                    logger.warning("No cookies left after removal. Waiting for 60 seconds.")
                    print("[INFO] No cookies left after removal. Waiting for 60 seconds.")
                    await asyncio.sleep(60)
                    new_cookies = await load_cookies()
                    if new_cookies:
                        cookie_list.extend(new_cookies)
                        for cookie in new_cookies:
                            cookie_usage[cookie] = 0
                            cookie_limits[cookie] = random.randint(5, 7)
                        logger.info(f"Added {len(new_cookies)} new cookies after removal")
                    else:
                        logger.error("No cookies available after waiting and removal. Exiting.")
                        print("[ERROR] No cookies available after waiting and removal. Exiting.")
                        return
                
                logger.info(f"Batch completed. Successful: {batch_success_count}/{batch_size}. Total processed this session: {processed_count}")
                
                # Adaptive delay based on success rate
                if batch_success_count == 0:
                    delay = 10  # Longer delay if no success
                    logger.info("No successful requests in batch, waiting 10 seconds")
                elif batch_success_count < batch_size // 2:
                    delay = 5   # Medium delay for low success rate
                    logger.info("Low success rate, waiting 5 seconds")
                else:
                    delay = 2   # Normal delay for good success rate
                
                await asyncio.sleep(delay)
        
        logger.info(f"Scraping completed. Total processed: {processed_count}")
        
        # Final status check
        remaining = safe_read_phone_numbers()
        logger.info(f"Final check: {len(remaining)} numbers remaining in phone_numbers.txt")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
       asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    logger.info("Starting scraper main function")
    try:
        asyncio.run(scraping())
        logger.info("Scraper completed successfully")
    except Exception as e:
        logger.error(f"Scraper failed with exception: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    finally:
        logger.info("Scraper script ending")
