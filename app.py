import fastf1
import time
import pandas as pd
from pythonosc import udp_client  

client = udp_client.SimpleUDPClient("127.0.0.1", 7000)

session = fastf1.get_session(2026, 1, 'R')
session.load(laps=True)

current_lap = 1

while current_lap <= 58:
    laps = session.laps.pick_laps(current_lap).sort_values(by='Position')
    
    for index, row in laps.iterrows():
        if pd.isna(row['Position']) or pd.isna(row['DriverNumber']):
            continue
        address = f"/driver/pos{int(row['Position'])}"
        print(address, int(row['DriverNumber']))
        client.send_message(address, int(row['DriverNumber']))
    
    time.sleep(10)
    current_lap += 1

print("Alle ronde data succesvol verzonden")