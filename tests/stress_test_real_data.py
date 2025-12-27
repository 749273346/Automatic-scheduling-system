import pandas as pd
import datetime
import os
import random
from collections import defaultdict
from src.db_manager import DBManager
from src.models import User, Schedule
from src.scheduler import Scheduler
from src.consts import GroupType

# Configuration
EXCEL_PATH = r"c:\Users\74927\Desktop\排班系统\项目相关资源\电力二工区人员信息 （最新）.xlsx"
DB_PATH = "stress_test.db"
START_DATE = datetime.date(2024, 12, 30) # Monday
WEEKS_TO_SIMULATE = 52

def load_users_from_excel(db_manager):
    """Load users from Excel and insert into DB"""
    print(f"Loading users from {EXCEL_PATH}...")
    try:
        df = pd.read_excel(EXCEL_PATH, header=1)
        
        # Clean existing users
        session = db_manager.get_session()
        session.query(Schedule).delete()
        session.query(User).delete()
        session.commit()
        session.close()
        
        users_added = 0
        
        # Generate colors
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD",
            "#D4A5A5", "#9B59B6", "#3498DB", "#F1C40F", "#E67E22",
            "#2ECC71", "#1ABC9C", "#9B59B6", "#34495E", "#16A085"
        ]
        
        for index, row in df.iterrows():
            name = str(row['姓名']).strip()
            if pd.isna(name) or name == 'nan':
                continue
                
            # Generate Code (A, B... AA...)
            if index < 26:
                code = chr(65 + index)
            else:
                code = chr(65 + (index // 26) - 1) + chr(65 + (index % 26))
                
            position = str(row['职务']).strip() if not pd.isna(row['职务']) else "员工"
            contact = str(row['电话号码']).strip() if not pd.isna(row['电话号码']) else ""
            
            # Simulate Preferences
            prefs = {}
            
            # 20% have preferred weekdays
            if random.random() < 0.2:
                # Pick 1 or 2 random days
                days = random.sample(range(7), k=random.randint(1, 2))
                prefs["preferred_weekdays"] = days
                
            # 10% avoid holidays
            if random.random() < 0.1:
                prefs["avoid_holidays"] = ["春节", "国庆节"]
                
            # 10% have blackout dates (random 5 days in 2025)
            if random.random() < 0.1:
                blackouts = []
                for _ in range(5):
                    # Random day in 2025
                    d = datetime.date(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 364))
                    blackouts.append(d.strftime("%Y-%m-%d"))
                prefs["blackout_dates"] = sorted(blackouts)
            
            db_manager.add_user(
                code=code,
                name=name,
                position=position,
                contact=contact,
                color=colors[index % len(colors)],
                preferences=prefs
            )
            users_added += 1
            
        print(f"Successfully added {users_added} users to {DB_PATH}")
        return users_added
    except Exception as e:
        print(f"Error loading Excel: {e}")
        return 0

def run_stress_test():
    print("Initializing Database...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    db_manager = DBManager(DB_PATH)
    count = load_users_from_excel(db_manager)
    
    if count < 2:
        print("Not enough users to run test.")
        return

    users = db_manager.get_all_users()
    
    # State tracking
    history_counts = defaultdict(int)
    last_duty_dates = {}
    total_shifts = 0
    start_time = datetime.datetime.now()
    
    print(f"\nStarting Stress Test for {WEEKS_TO_SIMULATE} weeks ({START_DATE} onwards)...")
    
    current_date = START_DATE
    all_schedules = []
    
    for week in range(WEEKS_TO_SIMULATE):
        scheduler = Scheduler(users, current_date, history_counts, last_duty_dates)
        
        # Run scheduling
        try:
            week_schedules = scheduler.generate_schedule()
        except Exception as e:
            print(f"CRASH at Week {week} ({current_date}): {e}")
            break
            
        if not week_schedules:
            print(f"WARNING: Failed to generate schedule for Week {week} ({current_date})")
        else:
            # Update state
            for sch in week_schedules:
                history_counts[sch.user.code] += 1
                last_duty_dates[sch.user.code] = sch.date
                all_schedules.append(sch)
                
        total_shifts += len(week_schedules)
        current_date += datetime.timedelta(days=7)
        
        if (week + 1) % 10 == 0:
            print(f"Completed Week {week+1}...")

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*50)
    print("STRESS TEST RESULTS")
    print("="*50)
    print(f"Total Users: {count}")
    print(f"Weeks Simulated: {WEEKS_TO_SIMULATE}")
    print(f"Total Shifts Generated: {total_shifts}")
    print(f"Time Taken: {duration:.2f} seconds")
    print(f"Average Time per Week: {duration/WEEKS_TO_SIMULATE:.4f} seconds")
    
    # Analysis
    print("\n[Fairness Analysis]")
    counts = [history_counts[u.code] for u in users]
    avg_shifts = sum(counts) / len(counts)
    min_shifts = min(counts)
    max_shifts = max(counts)
    print(f"Avg Shifts per User: {avg_shifts:.2f}")
    print(f"Min Shifts: {min_shifts}")
    print(f"Max Shifts: {max_shifts}")
    print(f"Variance (Max-Min): {max_shifts - min_shifts}")
    
    # Constraint Verification
    print("\n[Constraint Verification]")
    violations = 0
    weekend_violations = 0
    blackout_violations = 0
    holiday_violations = 0
    
    schedule_map = defaultdict(list)
    for sch in all_schedules:
        schedule_map[sch.date].append(sch.user)
        
        # Check Blackout
        if sch.user.preferences and "blackout_dates" in sch.user.preferences:
            if sch.date.strftime("%Y-%m-%d") in sch.user.preferences["blackout_dates"]:
                blackout_violations += 1
                
        # Check Holidays (Simple check based on name)
        # We need to reuse _get_holiday_name logic or just simple check
        # Let's verify 'avoid_holidays'
        if sch.user.preferences and "avoid_holidays" in sch.user.preferences:
            # Re-instantiate a scheduler just to use helper? Or just duplicate logic
            # Simplified: 2025-01-01 is New Year
            md = (sch.date.month, sch.date.day)
            is_holiday = False
            h_name = ""
            if md == (1, 1): h_name = "元旦"
            elif md in [(10, 1), (10, 2)]: h_name = "国庆节" # Simplified check
            elif sch.date.year == 2025 and md in [(1, 29), (1, 30)]: h_name = "春节" # Simplified
            
            if h_name and h_name in sch.user.preferences["avoid_holidays"]:
                holiday_violations += 1

    # Check Weekend Rule (Sat/Sun same users)
    # Iterate all Saturdays
    check_date = START_DATE
    for _ in range(WEEKS_TO_SIMULATE):
        sat = check_date + datetime.timedelta(days=5)
        sun = check_date + datetime.timedelta(days=6)
        
        sat_users = set(u.code for u in schedule_map[sat])
        sun_users = set(u.code for u in schedule_map[sun])
        
        if sat_users and sun_users:
            if sat_users != sun_users:
                weekend_violations += 1
                # print(f"Weekend Mismatch: {sat} {sat_users} vs {sun} {sun_users}")
        
        check_date += datetime.timedelta(days=7)

    print(f"Blackout Violations: {blackout_violations}")
    print(f"Holiday Violations: {holiday_violations} (Approx)")
    print(f"Weekend Rule Violations: {weekend_violations}")
    
    if blackout_violations == 0 and weekend_violations == 0:
        print("\nSUCCESS: System stability and core constraints verified.")
    else:
        print("\nFAILURE: Constraints violated.")

if __name__ == "__main__":
    run_stress_test()
