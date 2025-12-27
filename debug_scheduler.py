
import sys
import os
import datetime
from collections import defaultdict

# Add current directory to path
sys.path.append(os.getcwd())

from src.models import User, Schedule
from src.consts import GroupType
from src.scheduler import Scheduler
from src.db_manager import DBManager

def test_scheduler_crash():
    print("Initializing DB...")
    try:
        db_manager = DBManager()
        # db_manager.init_default_users() # Assuming already initialized
        users = db_manager.get_all_users()
        print(f"Loaded {len(users)} users.")
        
        if not users:
            print("No users found! Initializing defaults...")
            db_manager.init_default_users()
            users = db_manager.get_all_users()

        # Mock date
        start_date = datetime.date.today()
        # Find start of week (Monday)
        start_date = start_date - datetime.timedelta(days=start_date.weekday())
        print(f"Start date: {start_date}")

        # Mock existing schedules (empty for now, or fetch from DB)
        schedules = db_manager.get_all_schedules()
        
        # Prepare history counts
        history_counts = {}
        for s in schedules:
            if s.date < start_date:
                # Need to handle if s.user is loaded
                if s.user:
                    history_counts[s.user.code] = history_counts.get(s.user.code, 0) + 1
        
        print("History counts:", history_counts)

        print("Initializing Scheduler...")
        scheduler = Scheduler(users, start_date, history_counts=history_counts)
        
        print("Running generate_schedule...")
        # existing_locked could be empty for test
        week_schedules = scheduler.generate_schedule(existing_schedules=[])
        
        print(f"Generated {len(week_schedules)} schedules.")
        for s in week_schedules:
            print(f"{s.date}: {s.user.code}")
            
    except Exception as e:
        print("CRASHED!")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_scheduler_crash()
