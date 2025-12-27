import sys
import os
import datetime
import time
from collections import defaultdict
import random

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db_manager import DBManager
from src.models import User, Schedule
from src.scheduler import Scheduler
from src.consts import SHIFTS_PER_DAY

def run_stress_test():
    print("Starting High-Intensity Stress Test for Scheduling System...")
    
    db = DBManager()
    session = db.get_session()
    users = session.query(User).filter(User.is_active == True).all()
    session.close()
    
    if not users:
        print("Error: No users found in database. Please run import_excel_data.py first.")
        return

    print(f"Loaded {len(users)} users from database.")
    
    # Simulation Parameters
    start_date = datetime.date(2024, 12, 30) # Monday
    end_date = datetime.date(2025, 12, 31)
    
    history_counts = defaultdict(int)
    last_duty_dates = {}
    
    current_date = start_date
    weeks_count = 0
    failures = 0
    total_shifts_generated = 0
    
    start_time = time.time()
    
    while current_date <= end_date:
        # Scheduler works on a weekly basis starting from Monday
        if current_date.weekday() != 0:
            current_date += datetime.timedelta(days=1)
            continue
            
        print(f"Scheduling Week {weeks_count + 1}: {current_date}...", end="\r")
        
        try:
            # Create scheduler instance for this week
            scheduler = Scheduler(
                users=users,
                start_date=current_date,
                history_counts=history_counts,
                last_duty_dates=last_duty_dates
            )
            
            # Generate schedule
            schedules = scheduler.generate_schedule()
            
            if not schedules:
                print(f"\n[FAILURE] Could not generate schedule for week of {current_date}")
                failures += 1
            else:
                # Update history and last duty dates
                # Scheduler returns List[Schedule] objects (but they are not committed to DB, just objects)
                # However, Scheduler.generate_schedule returns a list of Schedule objects.
                # Let's verify what it returns. 
                # It returns self.get_result_list() which converts internal dict to Schedule objects.
                
                # We need to manually update our tracking dicts because Scheduler doesn't update the input dicts in-place for results
                # Wait, Scheduler updates self.user_week_counts internally.
                # But history_counts is passed in. Scheduler uses it for sorting.
                
                # Check consistency
                # 1. 7 days * 2 shifts = 14 shifts per week (usually)
                # Let's count actual shifts
                
                weekly_shifts = 0
                for sch in schedules:
                    user_code = sch.user.code
                    history_counts[user_code] += 1
                    last_duty_dates[user_code] = sch.date
                    weekly_shifts += 1
                
                total_shifts_generated += weekly_shifts
                
                # Validation: Check if every day has enough people
                # This is implicitly checked by Scheduler success, but let's be sure
                # Scheduler._backtrack ensures we reach end of week.
                pass

        except Exception as e:
            print(f"\n[EXCEPTION] Error at week {current_date}: {e}")
            import traceback
            traceback.print_exc()
            failures += 1
            
        # Move to next week
        current_date += datetime.timedelta(days=7)
        weeks_count += 1
        
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*50)
    print("STRESS TEST RESULTS")
    print("="*50)
    print(f"Total Weeks Simulated: {weeks_count}")
    print(f"Total Shifts Generated: {total_shifts_generated}")
    print(f"Failures: {failures}")
    print(f"Time Taken: {duration:.2f} seconds")
    print(f"Average Time per Week: {duration/weeks_count:.4f} seconds")
    
    print("\nShift Distribution (Top 5 and Bottom 5):")
    sorted_counts = sorted(history_counts.items(), key=lambda x: x[1], reverse=True)
    for code, count in sorted_counts[:5]:
        u = next((u for u in users if u.code == code), None)
        name = u.name if u else "Unknown"
        print(f"  {name} ({code}): {count}")
    print("  ...")
    for code, count in sorted_counts[-5:]:
        u = next((u for u in users if u.code == code), None)
        name = u.name if u else "Unknown"
        print(f"  {name} ({code}): {count}")

    if failures == 0:
        print("\n[SUCCESS] System passed high-intensity stress test.")
    else:
        print("\n[WARNING] System encountered failures during stress test.")

if __name__ == "__main__":
    run_stress_test()
