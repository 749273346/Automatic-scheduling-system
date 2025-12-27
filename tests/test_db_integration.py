from src.db_manager import DBManager
from src.models import User, Schedule
import datetime

def test_db():
    print("Initializing DBManager...")
    db = DBManager("test_schedule.db")
    db.init_default_users()
    
    users = db.get_all_users()
    print(f"Users count: {len(users)}")
    for u in users:
        print(f"User: {u.code}, Group: {u.group_type}")
        
    # Test Add Schedule
    today = datetime.date.today()
    print(f"Adding schedule for {today}...")
    user_a = users[0]
    db.add_schedule(today, user_a.id, is_locked=True)
    
    schedules = db.get_all_schedules()
    print(f"Schedules count: {len(schedules)}")
    if len(schedules) > 0:
        print(f"Schedule: {schedules[0].date} - {schedules[0].user.code}")
        
    print("Test finished.")

if __name__ == "__main__":
    test_db()
