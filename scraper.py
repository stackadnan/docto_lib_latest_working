
import asyncio
import random,sys
import logging
import threading
import os
import uuid
import time
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

# Ensure results directory exists
def ensure_results_directory():
    """Ensure the results directory exists."""
    try:
        os.makedirs("results", exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating results directory: {e}")
        return False

def generate_realistic_headers():
    """Generate realistic headers with randomized fingerprinting - cross-platform compatible"""
    
    # Detect platform for realistic headers
    is_linux = sys.platform.startswith('linux')
    is_windows = sys.platform.startswith('win')
    
    # Different Chrome versions
    chrome_versions = [
        "131.0.6778.85",
        "131.0.6778.69", 
        "130.0.6723.117",
        "130.0.6723.92",
        "129.0.6668.100",
        "129.0.6668.89"
    ]
    
    # Platform-specific configurations
    if is_linux:
        platform_name = "Linux"
        platform_versions = ["6.5.0", "6.1.0", "5.15.0", "5.4.0"]
        architectures = ["x86_64"]
        bitness_options = ["64"]
        user_agent_os = "X11; Linux x86_64"
    else:  # Windows or default
        platform_name = "Windows"
        platform_versions = ["15.0.0", "10.0.0", "13.0.0", "19.0.0"]
        architectures = ["x86", "arm64"]
        bitness_options = ["64", "32"]
        user_agent_os = "Windows NT 10.0; Win64; x64"
    
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
    
    # Generate consistent session ID
    session_components = ['cA1Y', 'bX2Z', 'dR3W', 'eT4V', 'mN8K', 'pQ5L']
    session_suffix = ['ckyz', 'mnop', 'qrst', 'uvwx', 'abcd', 'efgh']
    session_end = ['yC', 'zD', 'aE', 'bF', 'gH', 'iJ']
    
    session_id = f"c{random.randint(100000, 999999)}{random.choice(session_components)}{random.choice(session_suffix)}{random.randint(10, 99)}{random.choice(session_end)}"
    
    headers = {
        "Host": "www.doctolib.de",
        "Connection": "keep-alive",
        "sec-ch-ua": f'"Not)A;Brand";v="8", "Chromium";v="{major_version}", "Google Chrome";v="{major_version}"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": f'"{platform_name}"',
        "sec-ch-ua-platform-version": f'"{platform_version}"',
        "sec-ch-ua-arch": f'"{arch}"',
        "sec-ch-ua-bitness": f'"{bitness}"',
        "sec-ch-ua-model": '""',
        "sec-ch-ua-full-version": f'"{chrome_version}"',
        "User-Agent": f"Mozilla/5.0 ({user_agent_os}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.doctolib.de",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors", 
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.doctolib.de/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": language,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    return headers

print(f"Script started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Scraper started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Platform detected: {sys.platform}")
logger.info(f"Python version: {sys.version}")

# Ensure results directory exists at startup
if not ensure_results_directory():
    logger.error("Failed to create results directory. Exiting.")
    sys.exit(1)

def safe_remove_phone_number(phone_number):
    """Safely remove a phone number from the file with proper locking and error handling."""
    try:
        with file_lock:
            # Ensure directory exists
            if not ensure_results_directory():
                return False
                
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
            
            # Write back to file atomically
            temp_file = "results/phone_numbers.txt.tmp"
            try:
                with open(temp_file, "w", encoding='utf-8') as f:
                    if lines:
                        f.write("\n".join(lines) + "\n")
                    else:
                        f.write("")  # Empty file
                
                # Atomic move
                if os.path.exists("results/phone_numbers.txt"):
                    os.replace(temp_file, "results/phone_numbers.txt")
                else:
                    os.rename(temp_file, "results/phone_numbers.txt")
                    
                logger.debug(f"Successfully removed {phone_number}. Remaining: {len(lines)}")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise e
            
    except Exception as e:
        logger.error(f"Error removing phone number {phone_number}: {e}")
        return False

def safe_read_phone_numbers():
    """Safely read phone numbers from file with proper error handling."""
    try:
        with file_lock:
            # Ensure directory exists
            if not ensure_results_directory():
                return []
                
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
                # Ensure directory exists
                if not ensure_results_directory():
                    return False
                    
                # Add back to phone_numbers.txt for retry
                with open("results/phone_numbers.txt", "a", encoding='utf-8') as f:
                    f.write(f"{phone_number}\n")
                logger.info(f"Added {phone_number} for retry {retry_count}/{max_retries}")
                return True
        except Exception as e:
            logger.error(f"Error adding {phone_number} for retry: {e}")
    else:
        logger.warning(f"Phone number {phone_number} exceeded max retries ({max_retries}), giving up")
        # Write to not_registered as final fallback with file locking
        try:
            with file_lock:
                # Ensure directory exists
                if not ensure_results_directory():
                    return False
                    
                with open("results/not_registered.txt", "a", encoding='utf-8') as f:
                    f.write(f"{phone_number}\n")
        except Exception as e:
            logger.error(f"Error writing {phone_number} to not_registered.txt: {e}")
    
    return False

async def check_phone_number(session, phone_number, cookie, proxy, url):
    # Generate realistic headers for each request
    headers = generate_realistic_headers()
    headers["Cookie"] = f"dl_frcid={cookie}"  # Use proper case for Cookie header
    
    print(f"[INFO] Checking {phone_number} with cookie {cookie[:8]}...")
    logger.debug(f"Platform: {sys.platform}, Chrome version: {headers.get('sec-ch-ua-full-version', 'N/A')}")
    
    payload = {"username": phone_number, "clientId": "patient-de-client"}

    try:
        logger.debug(f"Checking phone number: {phone_number} with cookie: {cookie[:8]}...")
        
        # Add some delay for Linux to avoid being too aggressive
        if sys.platform.startswith('linux'):
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        async with session.post(url, json=payload, headers=headers, proxy=proxy, timeout=20) as response:
            if response.status == 200:
                data = await response.json()
                result = "registered" if data.get("account_exists") else "not_registered"
                logger.info(f"[OK] {phone_number} -> {result}")
                print(f"[OK] {phone_number} -> {result}")
                
                # Write to appropriate result file
                result_file = "results/registered.txt" if data.get("account_exists") else "results/not_registered.txt"
                try:
                    with file_lock:
                        # Ensure directory exists
                        if ensure_results_directory():
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
            elif response.status == 403:
                logger.warning(f"[FORBIDDEN] {phone_number} - Status 403, possible rate limiting")
                print(f"[FORBIDDEN] {phone_number} - Rate limited or blocked")
                
                # Add longer delay for Linux systems on 403
                if sys.platform.startswith('linux'):
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                
                return "rate_limited", cookie, phone_number
            elif response.status >= 500:
                logger.warning(f"[SERVER_ERROR] {phone_number} - Server error {response.status}")
                print(f"[SERVER_ERROR] {phone_number} - Server error {response.status}")
                
                return "server_error", cookie, phone_number
            else:
                logger.warning(f"[ERROR] {phone_number} failed. Status: {response.status}")
                print(f"[ERROR] {phone_number} failed. Status: {response.status}")
                response_text = await response.text()
                logger.warning(f"Response: {response_text[:200]}...")  # Limit response text
                print(f"Response: {response_text[:100]}...")
                
                # Return as invalid_cookie_no_retry so cookie gets removed but number doesn't get retried
                return "invalid_cookie_no_retry", cookie, phone_number
    except asyncio.TimeoutError:
        logger.error(f"[TIMEOUT] {phone_number} with cookie {cookie[:8]}... timed out")
        print(f"[TIMEOUT] {phone_number} with cookie failed: timeout")
        
        # Don't remove from phone_numbers.txt on timeout - retry later
        return "timeout", cookie, phone_number
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["10054", "forcibly closed", "connection reset", "broken pipe"]):
            logger.error(f"[CONNECTION_CLOSED] {phone_number} - Connection issue: {e}")
            print(f"[CONNECTION_CLOSED] {phone_number} - Connection forcibly closed")
            # Don't remove from phone_numbers.txt - this is likely rate limiting
            return "connection_closed", cookie, phone_number
        elif "ssl" in error_msg or "certificate" in error_msg:
            logger.error(f"[SSL_ERROR] {phone_number} - SSL/Certificate issue: {e}")
            print(f"[SSL_ERROR] {phone_number} - SSL/Certificate error")
            return "ssl_error", cookie, phone_number
        else:
            logger.error(f"[EXCEPTION] {phone_number} with cookie {cookie[:8]}... failed: {e}")
            print(f"[EXCEPTION] {phone_number} with cookie failed: {e}")
            
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
    
    # Update cookies.txt file with proper locking and error handling
    try:
        with file_lock:
            temp_file = "cookies.txt.tmp"
            try:
                with open(temp_file, "w", encoding='utf-8') as f:
                    if cookie_list:
                        f.write("\n".join(cookie_list) + "\n")
                    else:
                        f.write("")
                
                # Atomic move
                if os.path.exists("cookies.txt"):
                    os.replace(temp_file, "cookies.txt")
                else:
                    os.rename(temp_file, "cookies.txt")
                    
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise e
                
    except Exception as e:
        logger.error(f"Error updating cookies.txt: {e}")
    
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
    
    # Update cookies.txt file with proper locking and error handling
    try:
        with file_lock:
            temp_file = "cookies.txt.tmp"
            try:
                with open(temp_file, "w", encoding='utf-8') as f:
                    if cookie_list:
                        f.write("\n".join(cookie_list) + "\n")
                    else:
                        f.write("")
                
                # Atomic move
                if os.path.exists("cookies.txt"):
                    os.replace(temp_file, "cookies.txt")
                else:
                    os.rename(temp_file, "cookies.txt")
                    
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise e
                
    except Exception as e:
        logger.error(f"Error updating cookies.txt: {e}")
    
    logger.warning(f"Invalid cookie removed. Remaining cookies: {len(cookie_list)}")

async def load_cookies():
    try:
        with file_lock:
            with open("cookies.txt", "r", encoding='utf-8') as f:
                cookies = [line.strip() for line in f if line.strip()]
                logger.info(f"Loaded {len(cookies)} cookies from file")
                return cookies
    except FileNotFoundError:
        logger.warning("cookies.txt file not found")
        return []
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return []

async def scraping():
    url = "https://www.doctolib.de/authn/patient/realms/doctolib-patient/accounts/check_existence"
    
    # Platform-specific optimizations
    if sys.platform.startswith('linux'):
        logger.info("Running on Linux - applying platform-specific optimizations")
        # Pre-resolve DNS to avoid issues
        try:
            import socket
            socket.gethostbyname('www.doctolib.de')
            logger.info("DNS resolution successful for www.doctolib.de")
        except Exception as e:
            logger.warning(f"DNS resolution issue: {e}")
    else:
        logger.info("Running on Windows - using standard configuration")

    # Continuous loop to wait for phone numbers and cookies
    while True:
        # Load phone numbers initially
        phone_numbers = safe_read_phone_numbers()
        if not phone_numbers:
            logger.warning("No phone numbers found in phone_numbers.txt. Waiting for 60 seconds before checking again...")
            print("[INFO] No phone numbers found. Waiting for 60 seconds before checking again...")
            await asyncio.sleep(60)
            continue  # Go back to check for phone numbers again
        
        logger.info(f"Loaded {len(phone_numbers)} phone numbers to process")

        # Continuous loop to wait for cookies
        cookies = None
        while not cookies:
            cookies = await load_cookies()
            if not cookies:
                logger.warning("No cookies found in cookies.txt. Waiting for 60 seconds before checking again...")
                print("[INFO] No cookies found in cookies.txt. Waiting for 60 seconds before checking again...")
                await asyncio.sleep(60)
                # Also check if phone numbers still exist while waiting for cookies
                current_phone_numbers = safe_read_phone_numbers()
                if not current_phone_numbers:
                    logger.info("No phone numbers available while waiting for cookies. Breaking cookie wait loop.")
                    break
            else:
                logger.info(f"Found {len(cookies)} cookies, starting processing...")
                print(f"[INFO] Found {len(cookies)} cookies, starting processing...")

        # If no phone numbers available, continue outer loop
        if not cookies:
            continue

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

        # Create session with better connection handling and Linux compatibility
        import ssl
        
        # Create SSL context that works better across platforms
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE  # More permissive for cross-platform compatibility
        
        timeout = ClientTimeout(total=30, connect=15)  # Increased timeouts for Linux
        connector = TCPConnector(
            limit=10,  # Total connection pool size
            limit_per_host=5,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            enable_cleanup_closed=True,
            ssl=ssl_context  # Use custom SSL context
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
                    logger.info("No more phone numbers to process in this session.")
                    break  # Exit inner loop, will check for new numbers in outer loop
                
                # Check if we have too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}). Pausing for 1 minute.")
                    print(f"[ERROR] Too many consecutive errors. Pausing for 1 minute.")
                    await asyncio.sleep(60)
                    consecutive_errors = 0
                    continue
                
                logger.info(f"Processing batch with {len(current_numbers)} remaining numbers")
                
                # Platform-specific batch size adjustment
                if sys.platform.startswith('linux'):
                    base_batch_size = 2  # Smaller batches for Linux to be more conservative
                    max_batch_size = min(2, len(current_numbers))
                else:
                    base_batch_size = 3  # Standard batch size for Windows
                    max_batch_size = min(3, len(current_numbers))
                
                batch_size = max_batch_size
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
                            logger.warning("No cookies available after waiting. Ending this session.")
                            print("[INFO] No cookies available after waiting. Ending this session.")
                            break  # Exit processing loop, will restart in outer loop
                        cookie_list.extend(new_cookies)
                        for cookie in new_cookies:
                            cookie_usage[cookie] = 0
                            cookie_limits[cookie] = random.randint(5, 7)
                        logger.info(f"Added {len(new_cookies)} new cookies")

                    current_cookie = cookie_list[cookie_index % len(cookie_list)]
                    logger.debug(f"Using cookie {current_cookie[:8]}... for {phone_number}")
                    tasks.append(check_phone_number(session, phone_number, current_cookie, proxy, url))
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
                        
                        elif result_type == "rate_limited":
                            logger.warning(f"Rate limited for {phone_number}, adding back for retry")
                            if add_number_for_retry(phone_number):
                                logger.info(f"Added {phone_number} back for retry due to rate limiting")
                            consecutive_errors += 1
                            
                            # Add extra delay when rate limited on Linux
                            if sys.platform.startswith('linux'):
                                await asyncio.sleep(random.uniform(3.0, 8.0))
                        
                        elif result_type == "server_error":
                            logger.warning(f"Server error for {phone_number}, adding back for retry")
                            if add_number_for_retry(phone_number):
                                logger.info(f"Added {phone_number} back for retry due to server error")
                            consecutive_errors += 1
                        
                        elif result_type in ["timeout", "connection_closed", "ssl_error"]:
                            logger.warning(f"Network issue with {phone_number}: {result_type}")
                            # Add back for retry
                            if add_number_for_retry(phone_number):
                                logger.info(f"Added {phone_number} back for retry due to {result_type}")
                            consecutive_errors += 1
                            
                            # Platform-specific delays
                            if sys.platform.startswith('linux') and result_type in ["connection_closed", "ssl_error"]:
                                await asyncio.sleep(random.uniform(2.0, 5.0))
                        
                        else:  # exception
                            consecutive_errors += 1
                    
                    # Remove all invalid cookies
                    for invalid_cookie in invalid_cookies:
                        await remove_invalid_cookie(invalid_cookie, cookie_list, cookie_usage, cookie_limits)
                    
                    # Check if we need to reload cookies
                    if not cookie_list:
                        logger.warning("No cookies left after removal. Ending this session.")
                        print("[INFO] No cookies left after removal. Ending this session.")
                        break  # Exit inner loop, will wait for cookies in outer loop
                    
                    logger.info(f"Batch completed. Successful: {batch_success_count}/{batch_size}. Total processed this session: {processed_count}")
                    
                    # Platform-specific adaptive delay
                    if sys.platform.startswith('linux'):
                        # More conservative delays for Linux
                        if batch_success_count == 0:
                            delay = random.uniform(15, 25)  # Longer delay if no success
                            logger.info(f"No successful requests in batch (Linux), waiting {delay:.1f} seconds")
                        elif batch_success_count < batch_size // 2:
                            delay = random.uniform(8, 12)   # Medium delay for low success rate
                            logger.info(f"Low success rate (Linux), waiting {delay:.1f} seconds")
                        else:
                            delay = random.uniform(3, 6)   # Normal delay for good success rate
                            logger.info(f"Good success rate (Linux), waiting {delay:.1f} seconds")
                    else:
                        # Standard delays for Windows
                        if batch_success_count == 0:
                            delay = 10  # Longer delay if no success
                            logger.info("No successful requests in batch, waiting 10 seconds")
                        elif batch_success_count < batch_size // 2:
                            delay = 5   # Medium delay for low success rate
                            logger.info("Low success rate, waiting 5 seconds")
                        else:
                            delay = 2   # Normal delay for good success rate
                    
                    await asyncio.sleep(delay)
            
            logger.info(f"Session completed. Total processed this session: {processed_count}")
        
        # After session ends, check if we should continue
        remaining = safe_read_phone_numbers()
        logger.info(f"Session check: {len(remaining)} numbers remaining in phone_numbers.txt")
        
        if not remaining:
            logger.info("No more phone numbers to process. Waiting for 60 seconds before checking for new numbers...")
            print("[INFO] No more phone numbers to process. Waiting for 60 seconds before checking for new numbers...")
            await asyncio.sleep(60)
        else:
            logger.info("Phone numbers still available. Waiting 10 seconds before starting new session...")
            await asyncio.sleep(10)
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