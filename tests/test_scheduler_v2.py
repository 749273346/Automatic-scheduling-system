
import unittest
import datetime
from src.models import User, Schedule
from src.scheduler import Scheduler
from src.consts import GroupType

class TestSchedulerV2(unittest.TestCase):
    def setUp(self):
        # Setup 8 Users (A-H)
        self.users = []
        for i in range(8):
            code = chr(65 + i)
            u = User(id=i+1, code=code, group_type=GroupType.UNLIMITED, preferences={})
            self.users.append(u)
            
        # Monday
        self.start_date = datetime.date(2023, 1, 2) 

    def test_weekend_consistency(self):
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        # Convert to map: date -> [user_codes]
        schedule_map = {}
        for s in schedules:
            if s.date not in schedule_map:
                schedule_map[s.date] = []
            schedule_map[s.date].append(s.user.code)
            
        # Check Saturday (Index 5) and Sunday (Index 6)
        sat_date = self.start_date + datetime.timedelta(days=5)
        sun_date = self.start_date + datetime.timedelta(days=6)
        
        sat_users = sorted(schedule_map.get(sat_date, []))
        sun_users = sorted(schedule_map.get(sun_date, []))
        
        print(f"Saturday Users: {sat_users}")
        print(f"Sunday Users: {sun_users}")
        
        self.assertEqual(sat_users, sun_users, "Saturday and Sunday users should be the same")
        self.assertTrue(len(sat_users) > 0, "Should have users scheduled on weekend")

    def test_blackout_dates(self):
        # User A has blackout on Tuesday (Index 1)
        blackout_date = self.start_date + datetime.timedelta(days=1)
        self.users[0].preferences = {"blackout_dates": [blackout_date.strftime("%Y-%m-%d")]}
        
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        for s in schedules:
            if s.date == blackout_date:
                self.assertNotEqual(s.user.code, 'A', "User A should not be scheduled on blackout date")

    def test_avoid_pairing(self):
        # User A avoids User B
        self.users[0].preferences = {"avoid_pairing": ["B"]}
        
        scheduler = Scheduler(self.users, self.start_date)
        schedules = scheduler.generate_schedule()
        
        schedule_map = {}
        for s in schedules:
            if s.date not in schedule_map:
                schedule_map[s.date] = []
            schedule_map[s.date].append(s.user.code)
            
        for date, users in schedule_map.items():
            if 'A' in users and 'B' in users:
                self.fail(f"User A and B paired on {date} despite avoidance preference")

    def test_preferred_cycle(self):
        # User A prefers "每两周 (隔周)"
        self.users[0].preferences = {"preferred_cycle": "每两周 (隔周)"}
        
        # Scenario 1: Last duty was 2 weeks ago -> Should be available
        last_duty_dates = {'A': self.start_date - datetime.timedelta(days=14)}
        scheduler = Scheduler(self.users, self.start_date, last_duty_dates=last_duty_dates)
        
        # Ideally A should be scheduled (but it's not guaranteed unless we force it or check availability)
        # We can just check `check_constraints` directly
        self.assertTrue(scheduler.check_constraints(self.users[0], self.start_date))
        
        # Scenario 2: Last duty was last week -> Should NOT be available
        last_duty_dates = {'A': self.start_date - datetime.timedelta(days=5)} # Last Wednesday
        scheduler = Scheduler(self.users, self.start_date, last_duty_dates=last_duty_dates)
        self.assertFalse(scheduler.check_constraints(self.users[0], self.start_date))

if __name__ == '__main__':
    unittest.main()
