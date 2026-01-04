
import unittest
from collections import defaultdict
from src.scheduler import Scheduler
from src.models import User
import datetime

class TestSchedulerKeyError(unittest.TestCase):
    def test_key_error_h(self):
        # Create a user 'H'
        user_h = User(code='H', name='User H')
        users = [user_h]
        
        # Create history_counts as a plain dict, WITHOUT 'H'
        history_counts = {'A': 10} 
        
        start_date = datetime.date(2025, 1, 6) # Monday
        
        scheduler = Scheduler(users, start_date, history_counts=history_counts)
        
        # This should NOT raise KeyError anymore
        try:
            scheduler.generate_schedule()
        except KeyError as e:
            self.fail(f"Caught KeyError: {e}")
        except Exception as e:
            # Other exceptions might occur due to empty users list logic etc, but we care about KeyError 'H'
            pass

if __name__ == '__main__':
    unittest.main()
