import fastf1
import time
import pandas as pd
import bisect
import threading
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder


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
        self.driver_info = {}
        self.race_data = {}
        self.race_duration = 0.0
        self.total_laps = 0

    def load_session(self, year, round, session_type):
        fastf1.Cache.enable_cache(".fastf1_cache")
        print("Sessie laden...")
        self.session = fastf1.get_session(year, round, session_type)
        self.session.load(laps=True)

        self.driver_info = {}
        for _, driver in self.session.results.iterrows():
            self.driver_codes[driver["DriverNumber"]] = driver["Abbreviation"]
            color_hex = driver["TeamColor"]
            color_int = int(color_hex, 16) if color_hex else 0
            self.driver_info[driver["Abbreviation"]] = {
                "number": int(driver["DriverNumber"]),
                "color": color_int
            }

        self.preprocess()
        print(f"Data geladen: {len(self.driver_codes)} coureurs")
        for code, data in self.race_data.items():
            laps_count = len(data["times"])
            if laps_count > 0:
                print(
                    f"  {code}: {laps_count} laps ({data['times'][0]:.0f}s - {data['times'][-1]:.0f}s)")

    def preprocess(self):
        all_starts = self.session.laps["LapStartTime"].dropna()
        self.race_start_offset = all_starts.min().total_seconds()

        for driver_number, code in self.driver_codes.items():
            driver_laps = self.session.laps.pick_drivers(
                driver_number).sort_values("LapNumber")
            driver_data = []

            for _, lap in driver_laps.iterrows():
                if pd.isna(lap["LapStartTime"]):
                    continue
                race_time = lap["LapStartTime"].total_seconds() - \
                    self.race_start_offset
                position = lap["Position"]
                if pd.isna(position):
                    continue
                lap_duration = lap["LapTime"].total_seconds() if not pd.isna(
                    lap["LapTime"]) else 0.0
                driver_data.append(
                    (race_time, int(position), lap_duration))

            driver_data.sort(key=lambda x: x[0])
            self.race_data[code] = {
                "times": [t for t, _, _ in driver_data],
                "positions": [p for _, p, _ in driver_data],
                "durations": [d for _, _, d in driver_data],
                "code": code
            }

        all_times = []
        for data in self.race_data.values():
            if data["times"]:
                all_times.extend(data["times"])
        self.race_duration = max(all_times) if all_times else 0.0
        self.total_laps = int(self.session.laps["LapNumber"].max())
        print(
            f"Race duration: {self.race_duration:.0f} seconds ({self.race_duration/60:.0f} min)")
        print(f"Total laps: {self.total_laps}")

    def _get_track_position(self, driver_data, race_time):
        """Bereken track positie met decimale fractie door lap heen."""
        times = driver_data["times"]
        durations = driver_data["durations"]
        if not times:
            return 0.0, 0.0

        idx = bisect.bisect_right(times, race_time) - 1
        if idx < 0:
            return 0.0, 0.0
        if idx >= len(times):
            idx = len(times) - 1

        lap_start = times[idx]
        lap_dur = durations[idx] if durations[idx] > 0 else 80.0
        elapsed = race_time - lap_start
        fraction = min(elapsed / lap_dur, 1.0)
        track_pos = idx + fraction
        return track_pos, idx

    def get_state_at(self, race_time):
        drivers = {}
        for code, data in self.race_data.items():
            if not data["times"]:
                drivers[code] = {
                    "position": 99,
                    "number": self.driver_info.get(code, {}).get("number", 0),
                    "color": self.driver_info.get(code, {}).get("color", 16777215),
                    "interval": 0.0
                }
            else:
                idx = bisect.bisect_right(data["times"], race_time)
                if idx <= 1:
                    drivers[code] = {
                        "position": 99,
                        "number": self.driver_info.get(code, {}).get("number", 0),
                        "color": self.driver_info.get(code, {}).get("color", 16777215),
                        "interval": 0.0
                    }
                else:
                    pos = data["positions"][idx - 2]
                    drivers[code] = {
                        "position": pos,
                        "number": self.driver_info.get(code, {}).get("number", 0),
                        "color": self.driver_info.get(code, {}).get("color", 16777215),
                        "interval": 0.0
                    }

        sorted_drivers = sorted(
            drivers.items(), key=lambda x: x[1]["position"])

        prev_driver_code = None
        for code, data in sorted_drivers:
            if data["position"] == 99:
                continue

            if prev_driver_code is None:
                drivers[code]["interval"] = 0.0
            else:
                track_pos, lap_idx = self._get_track_position(
                    self.race_data[code], race_time)
                ahead_data = self.race_data[prev_driver_code]
                ahead_track_pos, ahead_lap_idx = self._get_track_position(
                    ahead_data, race_time)
                target_lap_idx = int(track_pos)

                interval = 0.0
                if target_lap_idx < len(ahead_data["durations"]):
                    ahead_dur = ahead_data["durations"][target_lap_idx]
                    if ahead_dur > 0:
                        target_time = ahead_data["times"][target_lap_idx] + \
                            (track_pos % 1) * ahead_dur
                        interval = race_time - target_time

                        if interval < 0:
                            if ahead_lap_idx == lap_idx:
                                curr_start = self.race_data[code]["times"][lap_idx]
                                ahead_start = ahead_data["times"][ahead_lap_idx]
                                if race_time >= curr_start and race_time >= ahead_start:
                                    interval = abs(
                                        (race_time - ahead_start) - (race_time - curr_start))
                                else:
                                    interval = abs(curr_start - ahead_start)
                            else:
                                interval = self.race_data[code]["times"][lap_idx] - \
                                    ahead_data["times"][ahead_lap_idx]
                    else:
                        ahead_start = ahead_data["times"][ahead_lap_idx]
                        if race_time >= ahead_start:
                            interval = race_time - ahead_start
                        else:
                            interval = abs(
                                self.race_data[code]["times"][lap_idx] - ahead_start)
                else:
                    last_ahead_time = ahead_data["times"][-1]
                    if race_time >= last_ahead_time:
                        interval = race_time - last_ahead_time
                    else:
                        interval = abs(
                            self.race_data[code]["times"][lap_idx] - last_ahead_time)

                drivers[code]["interval"] = round(max(0.0, interval), 3)

            prev_driver_code = code

        return drivers


class OSCBridge:
    def __init__(self, ip="127.0.0.1", port=7001):
        self.client_osc = udp_client.SimpleUDPClient(
            ip, port)  # Numerical data (7001)
        self.client_strings = udp_client.SimpleUDPClient(
            ip, 7002)  # String data (7002)

    def send_session_time(self, race_time):
        self.client_osc.send_message("/session/time", race_time)

    def send_driver(self, position, driver_code, number, color, interval):
        self.client_osc.send_message(f"/p{position}/code", driver_code)
        self.client_osc.send_message(f"/p{position}/number", number)
        self.client_osc.send_message(f"/p{position}/color", color)
        self.client_osc.send_message(f"/p{position}/interval", interval)

    def send_batch(self, drivers, race_time):
        self.send_session_time(race_time)
        sorted_drivers = sorted(
            drivers.items(), key=lambda x: x[1]["position"])
        for code, data in sorted_drivers:
            self.send_driver(data["position"], code,
                             data["number"], data["color"], data["interval"])

    def send_lap_info(self, current_lap, total_laps):
        self.client_osc.send_message("/race/lap/current", current_lap)
        self.client_osc.send_message("/race/lap/total", total_laps)

    def send_abbr_batch(self, sorted_drivers):
        abbr_list = [code for code, data in sorted_drivers]
        # Send as comma-separated string for easy parsing in TouchDesigner
        abbr_str = ",".join(abbr_list)
        self.client_strings.send_message("/race/abbreviations", abbr_str)


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
        self.input_thread = threading.Thread(
            target=self.handle_input, daemon=True)
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

                leader_code = None
                for code, data in state.items():
                    if data["position"] == 1:
                        leader_code = code
                        break

                current_lap = 0
                if leader_code and leader_code in self.data_engine.race_data:
                    leader_times = self.data_engine.race_data[leader_code]["times"]
                    current_lap = bisect.bisect_right(leader_times, race_time)

                self.osc.send_lap_info(
                    current_lap, self.data_engine.total_laps)

                sorted_state = sorted(
                    state.items(), key=lambda x: x[1]["position"])
                self.osc.send_abbr_batch(sorted_state)
                top5 = [f"{code}={data['position']}" for code,
                        data in sorted_state[:5]]
                dnf = [f"{code}" for code,
                       data in sorted_state if data["position"] == 99]
                dnf_str = f" DNF: {', '.join(dnf)}" if dnf else ""
                print(
                    f"\rTijd: {race_time:.1f}s | Top 5: {', '.join(top5)}{dnf_str}", end="", flush=True)

            time.sleep(self.tick_rate)

        self.cleanup()

    def cleanup(self):
        self.running = False
        print("\nPlayback gestopt")


if __name__ == "__main__":
    engine = PlaybackEngine()
    engine.setup()
    engine.run()
