# Scraper.py Continuous Operation Update

## Changes Made

### Problem Solved
- **Previous Behavior**: Scraper would exit if no cookies found after 60 seconds
- **New Behavior**: Scraper runs continuously, waiting for both phone numbers and cookies

### Key Improvements

#### 1. Continuous Operation Loop
```python
while True:  # Outer loop - never stops
    # Wait for phone numbers
    # Wait for cookies  
    # Process available numbers
    # Repeat
```

#### 2. Phone Number Waiting
- Checks for phone numbers every 60 seconds
- Logs status: "No phone numbers found. Waiting for 60 seconds before checking again..."
- Never exits due to missing phone numbers

#### 3. Cookie Waiting  
- Checks for cookies every 60 seconds
- Logs status: "No cookies found in cookies.txt. Waiting for 60 seconds before checking again..."
- Never exits due to missing cookies

#### 4. Session Management
- Creates new HTTP session for each batch processing cycle
- Ends session when no more numbers or cookies available
- Starts new session after waiting period

#### 5. Smart Coordination
- While waiting for cookies, also checks if phone numbers still exist
- Adapts to changing conditions (new files uploaded, new cookies generated)

## Behavior Flow

```
Start Scraper
    ↓
Check for Phone Numbers
    ↓ (if none found)
Wait 60 seconds → Check again
    ↓ (if found)
Check for Cookies
    ↓ (if none found)  
Wait 60 seconds → Check again
    ↓ (if found)
Start Processing Session
    ↓
Process Batches
    ↓ (when session ends)
Check for More Numbers/Cookies
    ↓
Repeat Forever
```

## Log Messages You'll See

### Waiting States:
- `"No phone numbers found. Waiting for 60 seconds before checking again..."`
- `"No cookies found in cookies.txt. Waiting for 60 seconds before checking again..."`

### Processing States:
- `"Found X cookies, starting processing..."`
- `"Loaded X phone numbers to process"`
- `"Session completed. Total processed this session: X"`

### Coordination States:
- `"No more phone numbers to process. Waiting for 60 seconds before checking for new numbers..."`
- `"Phone numbers still available. Waiting 10 seconds before starting new session..."`

## Benefits

1. **Never Stops**: Scraper runs 24/7 waiting for work
2. **Automatic Recovery**: Handles temporary absence of cookies or phone numbers
3. **Resource Efficient**: Uses proper session management
4. **Coordinated**: Works seamlessly with play_wright.py cookie generation
5. **Resilient**: Handles errors and network issues gracefully

## Usage

Simply start the scraper once:
```bash
python scraper.py
```

It will:
- Wait for phone_numbers.txt to appear
- Wait for cookies.txt to have cookies
- Process everything available
- Wait for new files/cookies
- Repeat indefinitely

## Perfect for Your Workflow

- **play_wright.py** generates cookies and saves them to cookies.txt
- **scraper.py** continuously monitors and processes using those cookies
- **telegram_bot.py** shows accurate progress from both processes
- Everything runs continuously without manual intervention!
