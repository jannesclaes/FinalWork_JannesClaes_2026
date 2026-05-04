import fastf1
import fastf1.plotting
import pandas as pd

fastf1.Cache.enable_cache('f1_cache')

session = fastf1.get_session(2024, 'Bahrain', 'Q')
session.load()

print("=== Session Info ===")
print(f"Race: {session.event['EventName']}")
print(f"Year: {session.event.year}")
print(f"Type: {session.name}")

print("\n=== Qualifying Results ===")
print(session.results)
