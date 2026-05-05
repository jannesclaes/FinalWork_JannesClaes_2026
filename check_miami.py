import fastf1
import pandas as pd

def check_miami():
    fastf1.Cache.enable_cache(".fastf1_cache")
    session = fastf1.get_session(2026, 4, 'R')
    session.load(laps=False)
    print(f"Sessie: {session.event['EventName']}")
    
    res = session.results[['Abbreviation', 'GridPosition', 'DriverNumber']]
    print(res.to_string())

if __name__ == "__main__":
    check_miami()
