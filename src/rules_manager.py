import json
import os
from typing import Dict, List, Any

class RulesManager:
    RULES_FILE = "schedule_rules.json"
    STATE_FILE = "schedule_state.json"

    DEFAULT_RULES = {
        "days": {
            "0": {"type": "loop", "users": []}, # Monday
            "1": {"type": "loop", "users": []}, # Tuesday
            "2": {"type": "loop", "users": []}, # Wednesday
            "3": {"type": "loop", "users": []}, # Thursday
            "4": {"type": "loop", "users": []}, # Friday
            "5": {"type": "loop", "users": []}, # Saturday
            "6": {"type": "follow_saturday", "users": []}, # Sunday
        },
        "loop_pool": [], # List of user codes in order
        "rotation_start_date": "2024-01-01" # Reference date for odd/even weeks
    }

    @classmethod
    def load_rules(cls) -> Dict[str, Any]:
        if not os.path.exists(cls.RULES_FILE):
            return cls.DEFAULT_RULES.copy()
        
        try:
            with open(cls.RULES_FILE, 'r', encoding='utf-8') as f:
                rules = json.load(f)
                # Ensure structure is valid (merge with defaults if keys missing)
                for k, v in cls.DEFAULT_RULES.items():
                    if k not in rules:
                        rules[k] = v
                return rules
        except Exception as e:
            print(f"Error loading rules: {e}")
            return cls.DEFAULT_RULES.copy()

    @classmethod
    def save_rules(cls, rules: Dict[str, Any]):
        with open(cls.RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=4, ensure_ascii=False)

    @classmethod
    def load_state(cls) -> Dict[str, Any]:
        if not os.path.exists(cls.STATE_FILE):
            return {"loop_index": 0}
        try:
            with open(cls.STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"loop_index": 0}

    @classmethod
    def save_state(cls, state: Dict[str, Any]):
        with open(cls.STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
