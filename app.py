import fastf1
from pythonosc import udp_client  

client = udp_client.SimpleUDPClient("127.0.0.1", 7000)

session = fastf1.get_session(2026, 1, 'R')
session.load(laps=True)
lap_12 = session.laps.pick_laps(12).sort_values(by='Position')

for index, row in lap_12.iterrows():
    address = f"/driver/pos{int(row['Position'])}"
    print(address, int(row['DriverNumber']))
    client.send_message(address, int(row['DriverNumber']))

print("Data succesvol verzonden")