import datetime
import unittest
from collections import defaultdict
from src.models import User
from src.scheduler import Scheduler
from src.consts import MAX_SHIFTS_PER_WEEK

class TestSchedulerNewRules(unittest.TestCase):
    def setUp(self):
        self.start_date = datetime.date(2023, 10, 23) # Monday
        self.users = []
        
        # User A: Level 1, Prefer Mon/Tue, Unavailable Wed
        u1 = User(code="A", name="UserA")
        u1.preferences = {
            "employee_type": "一级",
            "preferred_weekdays": [0, 1], # Mon, Tue
            "unavailable_dates": ["2023-10-25"] # Wed
        }
        self.users.append(u1)
        
        # User B: Level 2, Prefer Sat/Sun
        u2 = User(code="B", name="UserB")
        u2.preferences = {
            "employee_type": "二级",
            "preferred_weekdays": [5, 6]
        }
        self.users.append(u2)
        
        # User C: Level 3, No specific preference
        u3 = User(code="C", name="UserC")
        u3.preferences = {
            "employee_type": "三级"
        }
        self.users.append(u3)
        
        # User D: Level 1, Prefer Fri (Rotation)
        u4 = User(code="D", name="UserD")
        u4.preferences = {
            "employee_type": "一级",
            "preferred_weekdays": [4],
            "periodic_rotation": {
                "partner": "E",
                "day_idx": 4, # Friday
                "parity": "odd"
            }
        }
        self.users.append(u4)
        
        # User E: Level 1, Prefer Fri (Rotation)
        u5 = User(code="E", name="UserE")
        u5.preferences = {
            "employee_type": "一级",
            "preferred_weekdays": [4],
            "periodic_rotation": {
                "partner": "D",
                "day_idx": 4, # Friday
                "parity": "odd"
            }
        }
        self.users.append(u5)
        
        # User F: Unlimited, to fill gaps
        u6 = User(code="F", name="UserF")
        self.users.append(u6)
        u7 = User(code="G", name="UserG")
        self.users.append(u7)

    def test_level1_restriction(self):
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        # Check User A (Level 1)
        # Should ONLY work on Mon(0) or Tue(1)
        for sch in schedules:
            if sch.user.code == "A":
                self.assertIn(sch.date.weekday(), [0, 1])
                
    def test_weekend_consecutiveness(self):
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        # Check Weekend (Sat=5, Sun=6)
        sat_date = self.start_date + datetime.timedelta(days=5)
        sun_date = self.start_date + datetime.timedelta(days=6)
        
        sat_workers = [s.user.code for s in schedules if s.date == sat_date]
        sun_workers = [s.user.code for s in schedules if s.date == sun_date]
        
        # Logic: If assigned to Sat, MUST be assigned to Sun
        # And Sun workers must come from Sat workers
        self.assertEqual(set(sat_workers), set(sun_workers))
        self.assertTrue(len(sat_workers) > 0)

    def test_rotation_with_preference(self):
        # User D & E have rotation on Friday (4)
        # Both prefer Friday. So rotation should happen.
        # Week number of 2023-10-23 is 43 (Odd) -> D should work if parity=odd
        
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        fri_date = self.start_date + datetime.timedelta(days=4)
        fri_workers = [s.user.code for s in schedules if s.date == fri_date]
        
        # Since D is odd week, D should be scheduled (if slots allow)
        # E is partner. E should NOT be scheduled by rotation rule, but might be scheduled by normal rule?
        # But D is Level 1, restricted to Fri. E is Level 1, restricted to Fri.
        # If rotation picks D, D takes one slot.
        # Does E get picked? E prefers Fri. E is Level 1.
        # But rotation says "Alternate".
        # The rotation logic *applies* the rule. It doesn't ban the other.
        # But usually rotation implies exclusivity for that role?
        # The user said: "Take turns... Jia week 1, Yi week 2".
        # This implies for that *specific slot*, they rotate.
        # But if there are 2 slots per day?
        # Maybe both work?
        # But let's check if D is at least there.
        self.assertIn("D", fri_workers)
        
    def test_rotation_preference_dependency(self):
        # Modify D's preference to NOT include Friday
        # Then D should NOT be scheduled via rotation
        
        u_d = next(u for u in self.users if u.code == "D")
        u_d.preferences["preferred_weekdays"] = [0] # Mon only
        
        scheduler = Scheduler(self.users, self.start_date)
        # Rotation applies check: if day_idx not in preferred, skip.
        # So D should not be forced into Friday.
        # And since D is Level 1 and prefers Mon, D should only work Mon.
        
        schedules = scheduler.generate_schedule()
        fri_date = self.start_date + datetime.timedelta(days=4)
        fri_workers = [s.user.code for s in schedules if s.date == fri_date]
        
        self.assertNotIn("D", fri_workers)

if __name__ == '__main__':
    unittest.main()
