import datetime
import unittest
import os
from src.scheduler import Scheduler
from src.models import User, Schedule
from src.rules_manager import RulesManager

class TestNewScheduler(unittest.TestCase):
    def setUp(self):
        self.users = [
            User(id=1, code="A", name="User A"),
            User(id=2, code="B", name="User B"),
            User(id=3, code="C", name="User C"),
            User(id=4, code="D", name="User D"),
            User(id=5, code="E", name="User E")
        ]
        
        self.start_date = datetime.date(2024, 1, 1) # Monday
        
        # Define rules
        self.rules = {
            "days": {
                "0": {"type": "fixed", "users": ["A"]}, # Mon: A
                "1": {"type": "fixed", "users": ["B"]}, # Tue: B
                "2": {"type": "fixed", "users": ["C"]}, # Wed: C
                "3": {"type": "fixed", "users": ["B"]}, # Thu: B
                "4": {"type": "rotation", "users": ["A", "C"]}, # Fri: A/C rotate
                "5": {"type": "loop", "users": []}, # Sat: Loop
                "6": {"type": "follow_saturday", "users": []} # Sun: Follow Sat
            },
            "loop_pool": ["D", "E"],
            "rotation_start_date": "2024-01-01"
        }
        
    def test_week_1_schedule(self):
        # Week 1 (Odd week if starting 2024-01-01)
        # Week index 0. (Even? Wait, logic says week_num // 7. 0 is even.)
        # Logic: is_even_week = (week_num % 2 == 0).
        # week_num = 0. is_even_week = True.
        # Human logic: "Single week Hong, Double week Zheng".
        # If week 0 is "Single" or "Double"?
        # My code: 
        # current_week_count = week_num + 1 (1)
        # is_odd_week_human = (1 % 2 != 0) -> True.
        # If odd -> index 0 ("A").
        
        scheduler = Scheduler(self.users, self.start_date, loop_index=0, rules=self.rules)
        schedules = scheduler.generate_schedule()
        
        # Verify Mon (A)
        mon = [s for s in schedules if s.date == datetime.date(2024, 1, 1)]
        self.assertEqual(mon[0].user.code, "A")
        
        # Verify Fri (Rotation - Odd Week -> A)
        fri = [s for s in schedules if s.date == datetime.date(2024, 1, 5)]
        self.assertEqual(fri[0].user.code, "A")
        
        # Verify Sat (Loop -> D)
        sat = [s for s in schedules if s.date == datetime.date(2024, 1, 6)]
        self.assertEqual(sat[0].user.code, "D")
        
        # Verify Sun (Follow Sat -> D)
        sun = [s for s in schedules if s.date == datetime.date(2024, 1, 7)]
        self.assertEqual(sun[0].user.code, "D")
        
        # Verify Loop Index Update
        self.assertEqual(scheduler.new_loop_index, 1)

    def test_week_2_schedule(self):
        # Week 2 (Even week)
        start_date = datetime.date(2024, 1, 8)
        
        scheduler = Scheduler(self.users, start_date, loop_index=1, rules=self.rules)
        schedules = scheduler.generate_schedule()
        
        # Verify Fri (Rotation - Even Week -> C)
        fri = [s for s in schedules if s.date == datetime.date(2024, 1, 12)]
        self.assertEqual(fri[0].user.code, "C")
        
        # Verify Sat (Loop -> E)
        sat = [s for s in schedules if s.date == datetime.date(2024, 1, 13)]
        self.assertEqual(sat[0].user.code, "E")
        
        # Verify Loop Index Update
        self.assertEqual(scheduler.new_loop_index, 2)

    def test_loop_wrap_around(self):
        # Week 3 (Odd)
        start_date = datetime.date(2024, 1, 15)
        # loop_index = 2. Pool len = 2. 2%2 = 0 -> D.
        
        scheduler = Scheduler(self.users, start_date, loop_index=2, rules=self.rules)
        schedules = scheduler.generate_schedule()
        
        # Verify Sat (Loop -> D)
        sat = [s for s in schedules if s.date == datetime.date(2024, 1, 20)]
        self.assertEqual(sat[0].user.code, "D")

if __name__ == '__main__':
    unittest.main()
