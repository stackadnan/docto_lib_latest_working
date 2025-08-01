#!/usr/bin/env python3
"""
Test script to demonstrate the duplicate prevention fix in play_wright.py
"""

import os
import sys
import time
import threading
import random

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the fixed functions
from play_wright import get_next_phone_number, save_phone_result, remove_phone_from_file, cleanup_result_files, _processed_numbers

def create_test_phone_file():
    """Create a test phone numbers file"""
    os.makedirs("results", exist_ok=True)
    test_numbers = [f"491701234{i:03d}" for i in range(10)]  # 10 test numbers
    
    with open("results/phone_numbers.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(test_numbers) + "\n")
    
    print(f"✅ Created test file with {len(test_numbers)} phone numbers")
    return test_numbers

def simulate_concurrent_instances(instance_id, iterations=5):
    """Simulate what each browser instance does"""
    print(f"🚀 Instance {instance_id} started")
    
    for i in range(iterations):
        # Get next phone number (should be unique across instances)
        phone = get_next_phone_number()
        if phone is None:
            print(f"[{instance_id}] No more phone numbers available")
            break
            
        print(f"[{instance_id}] Got phone: {phone}")
        
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.3))
        
        # Simulate result (randomly registered or not)
        is_registered = random.choice([True, False])
        save_phone_result(phone, is_registered)
        remove_phone_from_file(phone)
        
        status = "REGISTERED" if is_registered else "NOT REGISTERED"
        print(f"[{instance_id}] Processed {phone} -> {status}")
        
        # Small delay between numbers
        time.sleep(0.1)
    
    print(f"✅ Instance {instance_id} completed")

def count_results():
    """Count results in files"""
    registered = 0
    not_registered = 0
    remaining = 0
    
    if os.path.exists("results/registered.txt"):
        with open("results/registered.txt", "r", encoding='utf-8') as f:
            registered = len([line.strip() for line in f if line.strip()])
    
    if os.path.exists("results/not_registered.txt"):
        with open("results/not_registered.txt", "r", encoding='utf-8') as f:
            not_registered = len([line.strip() for line in f if line.strip()])
    
    if os.path.exists("results/phone_numbers.txt"):
        with open("results/phone_numbers.txt", "r", encoding='utf-8') as f:
            remaining = len([line.strip() for line in f if line.strip()])
    
    return registered, not_registered, remaining

def main():
    print("🧪 Testing Duplicate Prevention Fix")
    print("=" * 50)
    
    # Clean up any existing files
    for filename in ["results/registered.txt", "results/not_registered.txt", "results/phone_numbers.txt"]:
        if os.path.exists(filename):
            os.remove(filename)
    
    # Create test file
    test_numbers = create_test_phone_file()
    initial_count = len(test_numbers)
    
    print(f"\n📊 Initial state:")
    print(f"   Total phone numbers: {initial_count}")
    
    # Simulate multiple concurrent instances (like the 20 browser instances)
    print(f"\n🚀 Starting 5 concurrent instances (simulating browser instances)...")
    
    threads = []
    for i in range(5):
        thread = threading.Thread(target=simulate_concurrent_instances, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print(f"\n📊 Final results:")
    registered, not_registered, remaining = count_results()
    total_processed = registered + not_registered
    
    print(f"   Registered: {registered}")
    print(f"   Not Registered: {not_registered}")
    print(f"   Total Processed: {total_processed}")
    print(f"   Remaining in file: {remaining}")
    print(f"   Numbers in memory set: {len(_processed_numbers)}")
    
    # Check for correctness
    print(f"\n✅ Verification:")
    expected_total = initial_count
    actual_total = total_processed + remaining
    
    if actual_total == expected_total:
        print(f"   ✅ PASSED: No duplicates detected!")
        print(f"   ✅ Expected total: {expected_total}, Actual total: {actual_total}")
    else:
        print(f"   ❌ FAILED: Numbers don't add up!")
        print(f"   ❌ Expected total: {expected_total}, Actual total: {actual_total}")
    
    # Check for duplicates in result files
    duplicate_check_passed = True
    
    if os.path.exists("results/registered.txt"):
        with open("results/registered.txt", "r", encoding='utf-8') as f:
            registered_numbers = [line.strip() for line in f if line.strip()]
        if len(registered_numbers) != len(set(registered_numbers)):
            print(f"   ❌ FAILED: Duplicates found in registered.txt!")
            duplicate_check_passed = False
    
    if os.path.exists("results/not_registered.txt"):
        with open("results/not_registered.txt", "r", encoding='utf-8') as f:
            not_registered_numbers = [line.strip() for line in f if line.strip()]
        if len(not_registered_numbers) != len(set(not_registered_numbers)):
            print(f"   ❌ FAILED: Duplicates found in not_registered.txt!")
            duplicate_check_passed = False
    
    if duplicate_check_passed:
        print(f"   ✅ PASSED: No duplicate entries in result files!")
    
    print(f"\n🎉 Test completed!")

if __name__ == "__main__":
    main()
