import fastf1
import pandas as pd
from app import DataEngine

def debug_start():
    engine = DataEngine()
    engine.load_session(2026, 4, 'R')
    
    for t in [0.0, 1.0, 5.0]:
        print(f"\n--- DEBUG (T={t}) ---")
        state = engine.get_state_at(t)
        sorted_state = sorted(state.items(), key=lambda x: x[1]['position'])
        for code, data in sorted_state[:5]:
            print(f"P{data['position']}: {code} (Grid: {data['official_position']}, Progress: {data['total_progress']:.4f})")

if __name__ == "__main__":
    debug_start()
