import fastf1
import time
import pandas as pd
import threading
from pythonosc import udp_client


class RaceClock:
    def __init__(self, speed_multiplier=1.0):
        self.state = "PAUSED"
        self.virtual_time = 0.0
        self.speed_multiplier = speed_multiplier
        self.last_real_time = None

    def start(self):
        if self.state == "PAUSED" or self.state == "IDLE":
            self.state = "RUNNING"
            self.last_real_time = time.perf_counter()
            print("Playback gestart")

    def pause(self):
        if self.state == "RUNNING":
            self.state = "PAUSED"
            self.last_real_time = None
            print("Playback gepauzeerd")

    def update(self):
        if self.state == "RUNNING" and self.last_real_time is not None:
            now = time.perf_counter()
            elapsed = now - self.last_real_time
            self.virtual_time += elapsed * self.speed_multiplier
            self.last_real_time = now

    def get_time(self):
        return self.virtual_time

    def is_running(self):
        return self.state == "RUNNING"


class DataEngine:
    def __init__(self):
        self.session = None
        self.driver_codes = {}
        self.race_data = {}
        self.race_duration = 0.0

    def load_session(self, year, round, session_type):
        fastf1.Cache.enable_cache(".fastf1_cache")
        print("Sessie laden...")
        self.session = fastf1.get_session(year, round, session_type)
        self.session.load(laps=True)

        for _, driver in self.session.results.iterrows():
            self.driver_codes[driver["DriverNumber"]] = driver["Abbreviation"]

        self.preprocess()
        print(f"Data geladen: {len(self.driver_codes)} coureurs")

    def preprocess(self):
        for driver_number, code in self.driver_codes.items():
            driver_laps = self.session.laps.pick_drivers(driver_number).sort_values("LapNumber")
            driver_data = []
            cumulative_time = 0.0

            for _, lap in driver_laps.iterrows():
                if pd.isna(lap["LapTime"]):
                    continue
                lap_time_seconds = lap["LapTime"].total_seconds()
                position = lap["Position"]
                if pd.isna(position):
                    continue
                driver_data.append((cumulative_time, int(position), code))
                cumulative_time += lap_time_seconds

            self.race_data[code] = driver_data

        max_time = max(data[-1][0] for data in self.race_data.values() if data)
        self.race_duration = max_time

    def get_state_at(self, race_time):
        positions = {}
        for code, data in self.race_data.items():
            if not data:
                continue
            position = 1
            for t, pos, _ in data:
                if race_time < t:
                    break
                position = pos
            positions[code] = position
        return positions


class OSCBridge:
    def __init__(self, ip="127.0.0.1", port=7001):
        self.client = udp_client.SimpleUDPClient(ip, port)

    def send_session_time(self, race_time):
        self.client.send_message("/session/time", race_time)

    def send_driver(self, driver_code, position):
        self.client.send_message(f"/driver/{driver_code}/position", position)

    def send_batch(self, positions, race_time):
        self.send_session_time(race_time)
        for code, pos in positions.items():
            self.send_driver(code, pos)


class PlaybackEngine:
    def __init__(self, year=2026, round=1, session_type="R", speed=1.0, tick_rate=1.0):
        self.clock = RaceClock(speed_multiplier=speed)
        self.data_engine = DataEngine()
        self.osc = OSCBridge(port=7001)
        self.tick_rate = tick_rate
        self.running = True
        self.input_thread = None

    def setup(self):
        self.data_engine.load_session(2026, 1, "R")
        self.input_thread = threading.Thread(target=self.handle_input, daemon=True)
        self.input_thread.start()

    def handle_input(self):
        while self.running:
            cmd = input().strip().lower()
            if cmd == "start":
                self.clock.start()
            elif cmd == "pause":
                self.clock.pause()
            elif cmd == "quit":
                self.running = False

    def run(self):
        print("\nControle commando's: start, pause, quit")
        print("Status: PAUSED\n")

        while self.running:
            self.clock.update()

            if self.clock.is_running():
                race_time = self.clock.get_time()

                if race_time >= self.data_engine.race_duration:
                    print("Race voltooid!")
                    break

                state = self.data_engine.get_state_at(race_time)
                self.osc.send_batch(state, race_time)
                print(f"\rTijd: {race_time:.1f}s | Coureurs: {len(state)}", end="", flush=True)

            time.sleep(self.tick_rate)

        self.cleanup()

    def cleanup(self):
        self.running = False
        print("\nPlayback gestopt")


if __name__ == "__main__":
    engine = PlaybackEngine()
    engine.setup()
    engine.run()