import fastf1

session = fastf1.get_session(2026, 1, 'R')

session.load()

lap_12 = session.laps.pick_laps(12).sort_values(by='Position')

print(lap_12[['Position', 'DriverNumber']])
