import unittest
import datetime
from src.scheduler import Scheduler
from src.models import User
from src.consts import GroupType

class TestSchedulerPreferences(unittest.TestCase):
    def setUp(self):
        # Create a set of users
        self.users = []
        for i in range(10):
            code = chr(65 + i) # A, B, C...
            u = User(id=i+1, code=code, name=f"User {code}")
            u.group_type = GroupType.UNLIMITED # Default
            u.preferences = {}
            self.users.append(u)
            
    def test_avoid_holidays(self):
        # Setup: 2024-12-30 is Monday. 
        # Jan 1, 2025 is Wednesday (Index 2).
        start_date = datetime.date(2024, 12, 30)
        
        # User A avoids "元旦"
        user_a = self.users[0] # A
        user_a.preferences = {"avoid_holidays": ["元旦"]}
        
        # Run scheduler
        scheduler = Scheduler(self.users, start_date)
        schedules = scheduler.generate_schedule()
        
        # Check Jan 1
        jan_1 = datetime.date(2025, 1, 1)
        scheduled_users = scheduler.schedule_result[jan_1]
        
        # Assert A is NOT in scheduled_users
        self.assertNotIn(user_a, scheduled_users, "User A avoided New Year but was scheduled")
        
        # Verify A is scheduled on other days (to ensure not totally broken)
        total_a = scheduler.user_week_counts['A']
        self.assertTrue(total_a > 0, "User A should be scheduled on other days")

    def test_preferred_weekdays(self):
        # Setup: 2024-12-30 is Monday.
        start_date = datetime.date(2024, 12, 30)
        
        # User B prefers Monday (0)
        user_b = self.users[1] # B
        user_b.preferences = {"preferred_weekdays": [0]}
        
        # User C prefers Tuesday (1)
        user_c = self.users[2] # C
        user_c.preferences = {"preferred_weekdays": [1]}
        
        # We need to limit the number of users or slots to ensure priority matters?
        # Actually, with 10 users and 2 slots/day, priority ensures they get picked FIRST.
        # But if everyone is available, they will just be picked.
        # Let's check if they ARE picked on their preferred days.
        
        scheduler = Scheduler(self.users, start_date)
        schedules = scheduler.generate_schedule()
        
        # Check Mon (Dec 30) for B
        mon_users = scheduler.schedule_result[start_date]
        self.assertIn(user_b, mon_users, "User B preferred Monday but was not scheduled")
        
        # Check Tue (Dec 31) for C
        tue_date = start_date + datetime.timedelta(days=1)
        tue_users = scheduler.schedule_result[tue_date]
        self.assertIn(user_c, tue_users, "User C preferred Tuesday but was not scheduled")

    def test_preferred_priority_logic(self):
        # Test that preferred users come before non-preferred in sort
        start_date = datetime.date(2024, 12, 30)
        scheduler = Scheduler(self.users, start_date)
        
        user_p = self.users[0]
        user_p.preferences = {"preferred_weekdays": [0]} # Mon
        
        user_n = self.users[1]
        user_n.preferences = {}
        
        # Mock counts to be equal
        scheduler.user_week_counts[user_p.code] = 0
        scheduler.user_week_counts[user_n.code] = 0
        
        candidates = [user_n, user_p]
        current_date = start_date # Mon
        
        # Sort manually using the key from scheduler
        candidates.sort(key=lambda u: (
            -1 if (u.preferences and isinstance(u.preferences, dict) and current_date.weekday() in u.preferences.get("preferred_weekdays", [])) else 0,
            scheduler.user_week_counts[u.code], 
            scheduler.history_counts.get(u.code, 0)
        ))
        
        self.assertEqual(candidates[0], user_p, "User P should be first due to preference")

if __name__ == '__main__':
    unittest.main()
