import datetime
import calendar

def verify_monday_start():
    # Test for January 2026
    # 2026-01-01 is a Thursday (3)
    
    current_date = datetime.date(2026, 1, 1)
    
    # 1. Logic simulation
    first_day = current_date.replace(day=1)
    start_weekday = first_day.weekday() # 0=Mon
    
    current_iter_date = first_day - datetime.timedelta(days=start_weekday)
    
    print(f"Target: 2026-01")
    print(f"First Day: {first_day}, Weekday: {first_day.weekday()} (3=Thu)")
    print(f"Start Iter Date (Top-Left of grid): {current_iter_date}")
    
    # Verify Top-Left is indeed the Monday of that week
    assert current_iter_date.weekday() == 0, "Top-left must be Monday"
    
    # Verify alignment
    # Row 0, Col 3 (index 3) should be Jan 1
    # current_iter_date is Col 0.
    # Col 3 date = current_iter_date + 3 days
    col3_date = current_iter_date + datetime.timedelta(days=3)
    print(f"Col 3 Date: {col3_date}")
    assert col3_date == first_day, "Col 3 should be Jan 1"
    
    print("Verification Passed!")

if __name__ == "__main__":
    verify_monday_start()
