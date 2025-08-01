import os
import asyncio
import logging
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import time
import threading
import subprocess
import signal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


os.makedirs("results", exist_ok=True)


# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables. Please check your .env file.")

RESULTS_FOLDER = "results"
PHONE_NUMBERS_FILE = os.path.join(RESULTS_FOLDER, "phone_numbers.txt")
REGISTERED_FILE = os.path.join(RESULTS_FOLDER, "registered.txt")
NOT_REGISTERED_FILE = os.path.join(RESULTS_FOLDER, "not_registered.txt")

# Global variable to track processing status
processing_active = False
processing_chat_id = None
playwright_process = None
scraper_process = None
initial_phone_count = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """
🤖 Welcome to Doctolib Phone Number Processor Bot!

📋 **How to use:**
1. Send me a text file containing phone numbers
2. I'll process them and check registration status
3. You'll receive the results when processing is complete

📁 **File Requirements:**
- Text file (.txt) format
- One phone number per line
- Any filename is accepted

🚀 **Available Commands:**
/start - Show this welcome message
/status - Check current processing status
/help - Show detailed help

**Ready to start? Send me your phone numbers file!**
    """
    
    await update.message.reply_text(welcome_message)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current processing status."""
    global processing_active, processing_chat_id, initial_phone_count
    
    try:
        if not processing_active:
            await update.message.reply_text("📊 **Status: Idle**\n\nNo processing currently active. Send a phone numbers file to start processing!")
            return
        
        # Count phone numbers in files
        phone_numbers_count = 0
        registered_count = 0
        not_registered_count = 0
        
        # Count remaining phone numbers
        if os.path.exists(PHONE_NUMBERS_FILE):
            with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                phone_numbers_count = len([line.strip() for line in lines if line.strip()])
        
        # Count registered numbers
        registered_numbers = set()
        if os.path.exists(REGISTERED_FILE):
            with open(REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                registered_numbers = set([line.strip() for line in lines if line.strip()])
                registered_count = len(registered_numbers)
        
        # Count not registered numbers
        not_registered_numbers = set()
        if os.path.exists(NOT_REGISTERED_FILE):
            with open(NOT_REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                not_registered_numbers = set([line.strip() for line in lines if line.strip()])
                not_registered_count = len(not_registered_numbers)
        
        # Remove any overlap to avoid double counting (prioritize registered status)
        if registered_numbers and not_registered_numbers:
            overlap = registered_numbers.intersection(not_registered_numbers)
            if overlap:
                not_registered_count = len(not_registered_numbers - registered_numbers)
        
        # Calculate progress
        total_processed = registered_count + not_registered_count
        progress_percentage = (total_processed / initial_phone_count * 100) if initial_phone_count > 0 else 0
        
        # Check if processing is complete
        if total_processed >= initial_phone_count:
            status_message = f"""
📊 **Status: Processing Complete!**

📱 **Initial Numbers:** {initial_phone_count}
✅ **Registered:** {registered_count}
❌ **Not Registered:** {not_registered_count}
� **Total Processed:** {total_processed}
🔄 **Remaining in File:** {phone_numbers_count}
📈 **Progress:** {progress_percentage:.1f}%

🎉 All numbers processed! Sending results now...
            """
        else:
            status_message = f"""
📊 **Status: Processing Active**

📱 **Initial Numbers:** {initial_phone_count}
✅ **Registered:** {registered_count}
❌ **Not Registered:** {not_registered_count}
� **Total Processed:** {total_processed}
🔄 **Remaining in File:** {phone_numbers_count}
📈 **Progress:** {progress_percentage:.1f}%

⏳ Processing is ongoing...
            """
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text("❌ Error getting status information.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads."""
    global processing_active, processing_chat_id
    
    document: Document = update.message.document
    
    # Check if it's a text file
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            "❌ Please send a text file (.txt) containing phone numbers."
        )
        return
    
    try:
        # Download the file
        file = await context.bot.get_file(document.file_id)
        
        # Ensure results folder exists
        os.makedirs(RESULTS_FOLDER, exist_ok=True)
        
        # Save as phone_numbers.txt
        await file.download_to_drive(PHONE_NUMBERS_FILE)
        
        # Count phone numbers and clean up the file
        unique_phones = set()
        with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                phone = line.strip()
                if phone:  # Only count non-empty lines
                    unique_phones.add(phone)
        
        # Rewrite the file with only unique phone numbers
        with open(PHONE_NUMBERS_FILE, 'w', encoding='utf-8') as f:
            for phone in unique_phones:
                f.write(phone + '\n')
        
        phone_count = len(unique_phones)
        original_count = len([line.strip() for line in lines if line.strip()])
        
        # Send confirmation message
        if original_count != phone_count:
            confirmation_message = f"""
✅ File received and validated!
📱 Original Numbers: {original_count}
🔄 Unique Numbers: {phone_count} (duplicates removed)
🚀 Starting processing now...
I'll notify you when the processing is complete!
            """
        else:
            confirmation_message = f"""
✅ File received and validated!
📱 Phone Numbers: {phone_count}
🚀 Starting processing now...
I'll notify you when the processing is complete!
            """
        
        await update.message.reply_text(confirmation_message)
        
        # Start monitoring process
        processing_active = True
        processing_chat_id = update.effective_chat.id
        
        # Store initial count globally
        global initial_phone_count
        initial_phone_count = phone_count
        
        # Start the processing services
        start_processing_services()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_processing, args=(context.bot,))
        monitor_thread.daemon = True
        monitor_thread.start()
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text(
            "❌ Error processing file. Please try again."
        )

def start_processing_services():
    """Start play_wright.py and then scraper.py after 1 minute."""
    global playwright_process, scraper_process
    
    try:
        # Get the Python executable path
        import sys
        python_executable = sys.executable
        
        # Start play_wright.py
        logger.info("Starting play_wright.py...")
        playwright_process = subprocess.Popen(
            [python_executable, "play_wright.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logger.info(f"play_wright.py started with PID: {playwright_process.pid}")
        
        # Start scraper.py after 1 minute
        def start_scraper():
            time.sleep(60)  # Wait 1 minute
            try:
                global scraper_process
                logger.info("Starting scraper.py...")
                scraper_process = subprocess.Popen(
                    [python_executable, "scraper.py"],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logger.info(f"scraper.py started with PID: {scraper_process.pid}")
            except Exception as e:
                logger.error(f"Error starting scraper.py: {e}")
        
        # Start scraper in a separate thread
        scraper_thread = threading.Thread(target=start_scraper)
        scraper_thread.daemon = True
        scraper_thread.start()
        
    except Exception as e:
        logger.error(f"Error starting processing services: {e}")

def stop_processing_services():
    """Stop both play_wright.py and scraper.py processes."""
    global playwright_process, scraper_process
    
    try:
        if playwright_process and playwright_process.poll() is None:
            logger.info("Stopping play_wright.py...")
            playwright_process.terminate()
            try:
                playwright_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                playwright_process.kill()
            logger.info("play_wright.py stopped")
        
        if scraper_process and scraper_process.poll() is None:
            logger.info("Stopping scraper.py...")
            scraper_process.terminate()
            try:
                scraper_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                scraper_process.kill()
            logger.info("scraper.py stopped")
            
    except Exception as e:
        logger.error(f"Error stopping processing services: {e}")

def monitor_processing(bot):
    """Monitor the phone_numbers.txt file and send results when complete."""
    global processing_active, processing_chat_id, initial_phone_count
    
    logger.info(f"Starting monitoring with {initial_phone_count} initial phone numbers")
    
    while processing_active:
        try:
            # Count phone numbers in files
            phone_numbers_count = 0
            registered_count = 0
            not_registered_count = 0
            
            # Count remaining phone numbers
            if os.path.exists(PHONE_NUMBERS_FILE):
                with open(PHONE_NUMBERS_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    phone_numbers_count = len([line.strip() for line in lines if line.strip()])
            
            # Count registered numbers
            if os.path.exists(REGISTERED_FILE):
                with open(REGISTERED_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    registered_numbers = set([line.strip() for line in lines if line.strip()])
                    registered_count = len(registered_numbers)
            
            # Count not registered numbers
            if os.path.exists(NOT_REGISTERED_FILE):
                with open(NOT_REGISTERED_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    not_registered_numbers = set([line.strip() for line in lines if line.strip()])
                    not_registered_count = len(not_registered_numbers)
            
            # Remove any overlap between registered and not_registered to avoid double counting
            if os.path.exists(REGISTERED_FILE) and os.path.exists(NOT_REGISTERED_FILE):
                overlap = registered_numbers.intersection(not_registered_numbers)
                if overlap:
                    logger.warning(f"Found {len(overlap)} overlapping numbers between registered and not_registered files")
                    # Prioritize registered status and remove from not_registered count
                    not_registered_count = len(not_registered_numbers - registered_numbers)
            
            total_processed = registered_count + not_registered_count
            
            logger.info(f"Monitoring: initial={initial_phone_count}, remaining={phone_numbers_count}, registered={registered_count}, not_registered={not_registered_count}, total_processed={total_processed}")
            
            # Check if processing is complete using multiple criteria:
            # Option 1: All numbers from initial count have been processed
            # Option 2: Phone numbers file is empty and we have some results
            # Option 3: No change in counts for extended period (stuck state)
            
            processing_complete = False
            
            if total_processed >= initial_phone_count and initial_phone_count > 0:
                logger.info("Processing complete: All initial phone numbers have been processed")
                processing_complete = True
            elif phone_numbers_count == 0 and total_processed > 0:
                logger.info("Processing complete: Phone numbers file is empty and we have results")
                processing_complete = True
            elif phone_numbers_count > 0 and total_processed >= initial_phone_count:
                logger.info("Processing complete: Processed count matches or exceeds initial count, remaining numbers might be duplicates/invalid")
                processing_complete = True
            
            if processing_complete:
                # Processing is complete, stop services and send results
                logger.info("Stopping services and sending results...")
                stop_processing_services()
                
                # Send results synchronously using asyncio.run
                try:
                    asyncio.run(send_results(bot, processing_chat_id))
                    logger.info("Results sent successfully!")
                except Exception as e:
                    logger.error(f"Error sending results: {e}")
                    # Try to send at least an error message
                    try:
                        asyncio.run(bot.send_message(
                            chat_id=processing_chat_id,
                            text="❌ Error sending results. Processing completed but failed to send files. Please check manually."
                        ))
                    except Exception as e2:
                        logger.error(f"Failed to send error message: {e2}")
                
                processing_active = False
                break
                
        except Exception as e:
            logger.error(f"Error monitoring file: {e}")
        
        # Wait 5 seconds before checking again
        time.sleep(5)

def cleanup_result_files():
    """Remove duplicate entries from result files and handle overlaps."""
    try:
        registered_numbers = set()
        not_registered_numbers = set()
        
        # Read registered numbers
        if os.path.exists(REGISTERED_FILE):
            with open(REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                registered_numbers = set([line.strip() for line in lines if line.strip()])
        
        # Read not registered numbers
        if os.path.exists(NOT_REGISTERED_FILE):
            with open(NOT_REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                not_registered_numbers = set([line.strip() for line in lines if line.strip()])
        
        # Remove overlaps (prioritize registered status)
        if registered_numbers and not_registered_numbers:
            overlap = registered_numbers.intersection(not_registered_numbers)
            if overlap:
                logger.info(f"Cleaning up {len(overlap)} overlapping numbers from not_registered file")
                not_registered_numbers = not_registered_numbers - registered_numbers
        
        # Rewrite files with cleaned data
        if registered_numbers:
            with open(REGISTERED_FILE, 'w', encoding='utf-8') as f:
                for number in sorted(registered_numbers):
                    f.write(f"{number}\n")
            logger.info(f"Cleaned registered.txt: {len(registered_numbers)} unique numbers")
        
        if not_registered_numbers:
            with open(NOT_REGISTERED_FILE, 'w', encoding='utf-8') as f:
                for number in sorted(not_registered_numbers):
                    f.write(f"{number}\n")
            logger.info(f"Cleaned not_registered.txt: {len(not_registered_numbers)} unique numbers")
    
    except Exception as e:
        logger.error(f"Error cleaning result files: {e}")

async def send_results(bot, chat_id):
    """Send the result files to the user."""
    try:
        logger.info(f"Starting send_results function for chat_id: {chat_id}")
        
        # Clean up duplicate entries in result files before sending
        cleanup_result_files()
        
        # Count final results with deduplication
        registered_numbers = set()
        not_registered_numbers = set()
        
        if os.path.exists(REGISTERED_FILE):
            with open(REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                registered_numbers = set([line.strip() for line in lines if line.strip()])
                registered_count = len(registered_numbers)
            logger.info(f"Found {registered_count} unique registered numbers")
        
        if os.path.exists(NOT_REGISTERED_FILE):
            with open(NOT_REGISTERED_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                not_registered_numbers = set([line.strip() for line in lines if line.strip()])
                not_registered_count = len(not_registered_numbers)
            logger.info(f"Found {not_registered_count} unique not registered numbers")
        
        # Remove overlaps (prioritize registered status)
        if registered_numbers and not_registered_numbers:
            overlap = registered_numbers.intersection(not_registered_numbers)
            if overlap:
                logger.warning(f"Found {len(overlap)} overlapping numbers, prioritizing registered status")
                not_registered_count = len(not_registered_numbers - registered_numbers)
        
        # Send completion message with summary
        completion_message = f"""
🎉 **Processing Completed Successfully!**

📊 **Final Results:**
✅ **Registered:** {registered_count}
❌ **Not Registered:** {not_registered_count}
📱 **Total Processed:** {registered_count + not_registered_count}

📁 **Sending result files now...**
        """
        
        logger.info("Sending completion message...")
        await bot.send_message(chat_id=chat_id, text=completion_message)
        logger.info("Completion message sent successfully!")
        
        # Send registered.txt if it exists
        if os.path.exists(REGISTERED_FILE) and os.path.getsize(REGISTERED_FILE) > 0:
            logger.info("Sending registered file...")
            with open(REGISTERED_FILE, 'rb') as file:
                await bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=f"📱 Registered phone numbers ({registered_count} total)"
                )
            logger.info("Registered file sent successfully!")
        else:
            logger.info("No registered file to send")
            await bot.send_message(
                chat_id=chat_id,
                text="📱 No registered phone numbers found."
            )
        
        # Send not_registered.txt if it exists
        if os.path.exists(NOT_REGISTERED_FILE) and os.path.getsize(NOT_REGISTERED_FILE) > 0:
            logger.info("Sending not registered file...")
            with open(NOT_REGISTERED_FILE, 'rb') as file:
                await bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=f"❌ Not registered phone numbers ({not_registered_count} total)"
                )
            logger.info("Not registered file sent successfully!")
        else:
            logger.info("No not registered file to send")
            await bot.send_message(
                chat_id=chat_id,
                text="❌ No unregistered phone numbers found."
            )
        
        # Clean up files
        logger.info("Cleaning up files...")
        cleanup_files()
        
        # Send final message
        logger.info("Sending final message...")
        await bot.send_message(
            chat_id=chat_id,
            text="✅ **All files sent and cleaned up!**\n\nReady for next processing. Send another file to start again! 🚀"
        )
        logger.info("Final message sent successfully!")
        
    except Exception as e:
        logger.error(f"Error in send_results: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Error sending results. Please contact support."
            )
        except Exception as e2:
            logger.error(f"Failed to send error message: {e2}")

def cleanup_files():
    """Delete the three files after sending results."""
    files_to_delete = [PHONE_NUMBERS_FILE, REGISTERED_FILE, NOT_REGISTERED_FILE]
    
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
🤖 **Doctolib Phone Number Processor Bot Help**

**Available Commands:**
/start - Start the bot and see welcome message
/status - Check current processing status and progress
/help - Show this help message

**How to use:**
1. Send a .txt file with phone numbers (one per line)
2. The bot will process them automatically
3. Use /status to check progress anytime
4. You'll receive results when processing is complete

**File format example:**
```
+33123456789
+33987654321
+33555666777
```

**Processing Logic:**
- Bot starts play_wright.py immediately
- After 1 minute, starts scraper.py
- Monitors progress continuously
- When registered + not_registered = total phone numbers → sends results
- Automatically stops services and cleans up files

Need more help? Contact support!
    """
    await update.message.reply_text(help_text)

def main() -> None:
    """Start the bot."""
    try:
        # Create custom request with longer timeout
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=60.0,
            read_timeout=60.0,
            write_timeout=60.0,
            pool_timeout=10.0
        )
        
        # Create the Application with custom request
        application = Application.builder().token(BOT_TOKEN).request(request).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        # Run the bot until the user presses Ctrl-C
        print("🤖 Bot is starting...")
        print(f"� Using token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
        print("⏳ Testing connection to Telegram...")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=60,
            bootstrap_retries=5
        )
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("💡 Please check your .env file and ensure all required variables are set.")
        print("📄 See .env.example for the required format.")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopping...")
        stop_processing_services()
        print("✅ Bot stopped successfully!")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        print(f"❌ Bot failed to start: {e}")
        stop_processing_services()

if __name__ == '__main__':
    main()