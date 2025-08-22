#!/usr/bin/env python3
"""
Test script to verify shift calculation logic with Czech timezone
"""

import pytz
from datetime import datetime

# Define Czech timezone
CZECH_TIMEZONE = pytz.timezone('Europe/Prague')

def get_shift_from_czech_datetime(dt):
    """
    Determine which shift a datetime falls into based on Czech timezone
    Shifts:
    - Morning: 6:00-14:00 (6 AM to 2 PM)
    - Evening: 14:00-22:00 (2 PM to 10 PM)
    - Night: 22:00-6:00 (10 PM to 6 AM, crosses midnight)
    """
    if dt is None:
        return 'Unknown'
    
    # Convert to Czech timezone
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    czech_time = dt.astimezone(CZECH_TIMEZONE)
    
    hour = czech_time.hour
    
    if 6 <= hour < 14:
        return 'Morning'
    elif 14 <= hour < 22:
        return 'Evening'
    else:  # hour >= 22 or hour < 6
        return 'Night'

def test_shift_logic():
    """Test the shift logic with various times"""
    
    # Test cases: (UTC time, expected shift)
    test_cases = [
        # Morning shift tests (6-14 Czech time)
        ('2024-01-15 05:00:00', 'Morning'),  # 6:00 Czech (CET = UTC+1)
        ('2024-01-15 08:30:00', 'Morning'),  # 9:30 Czech  
        ('2024-01-15 12:59:00', 'Morning'),  # 13:59 Czech
        
        # Evening shift tests (14-22 Czech time)  
        ('2024-01-15 13:00:00', 'Evening'),  # 14:00 Czech
        ('2024-01-15 16:00:00', 'Evening'),  # 17:00 Czech
        ('2024-01-15 20:59:00', 'Evening'),  # 21:59 Czech
        
        # Night shift tests (22-6 Czech time)
        ('2024-01-15 21:00:00', 'Night'),    # 22:00 Czech
        ('2024-01-15 23:30:00', 'Night'),    # 0:30 next day Czech
        ('2024-01-16 03:00:00', 'Night'),    # 4:00 Czech
        ('2024-01-16 04:59:00', 'Night'),    # 5:59 Czech
        
        # Summer time tests (CEST = UTC+2)
        ('2024-07-15 04:00:00', 'Morning'),  # 6:00 Czech (CEST)
        ('2024-07-15 12:00:00', 'Evening'),  # 14:00 Czech (CEST) 
        ('2024-07-15 20:00:00', 'Night'),    # 22:00 Czech (CEST)
    ]
    
    print("🔍 Testing shift calculation logic...")
    print("=" * 60)
    
    all_passed = True
    
    for utc_time_str, expected_shift in test_cases:
        # Create UTC datetime
        utc_dt = datetime.fromisoformat(utc_time_str)
        utc_dt = pytz.UTC.localize(utc_dt)
        
        # Convert to Czech time for display
        czech_dt = utc_dt.astimezone(CZECH_TIMEZONE)
        
        # Get calculated shift
        calculated_shift = get_shift_from_czech_datetime(utc_dt)
        
        # Check result
        passed = calculated_shift == expected_shift
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"{status} | UTC: {utc_time_str} | Czech: {czech_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} | Expected: {expected_shift} | Got: {calculated_shift}")
        
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests passed! Shift logic is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the shift logic.")
    
    return all_passed

if __name__ == "__main__":
    test_shift_logic()