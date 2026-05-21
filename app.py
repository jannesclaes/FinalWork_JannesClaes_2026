import os
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
            grid_pos = int(driver["GridPosition"]) if not pd.isna(driver["GridPosition"]) else 99
            self.driver_info[driver["Abbreviation"]] = {
                "number": int(driver["DriverNumber"]),
                "color": color_int,
                "grid_position": grid_pos
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

        # Track status preprocessing
        self.track_status_data = []
        for _, row in self.session.track_status.iterrows():
            race_time = row["Time"].total_seconds() - self.race_start_offset
            self.track_status_data.append((race_time, row["Status"]))
        self.track_status_data.sort(key=lambda x: x[0])

        # Global bests for session
        global_best_s1 = self.session.laps["Sector1Time"].min()
        global_best_s2 = self.session.laps["Sector2Time"].min()
        global_best_s3 = self.session.laps["Sector3Time"].min()

        for driver_number, code in self.driver_codes.items():
            driver_laps = self.session.laps.pick_drivers(
                driver_number).sort_values("LapNumber")
            driver_data = []
            sector_data = []

            grid_pos = self.driver_info[code]["grid_position"]
            prev_position = grid_pos
            
            # Personal bests "so far"
            p_best_s1 = pd.Timedelta(days=1)
            p_best_s2 = pd.Timedelta(days=1)
            p_best_s3 = pd.Timedelta(days=1)
            p_best_lap = float('inf')

            for _, lap in driver_laps.iterrows():
                if pd.isna(lap["LapStartTime"]):
                    continue
                race_time = lap["LapStartTime"].total_seconds() - \
                    self.race_start_offset
                start_position = prev_position
                end_position = int(lap["Position"]) if not pd.isna(
                    lap["Position"]) else prev_position
                lap_duration = lap["LapTime"].total_seconds() if not pd.isna(
                    lap["LapTime"]) else 0.0
                
                # Tire info mapping
                compound_str = lap["Compound"] if not pd.isna(lap["Compound"]) else "UNKNOWN"
                compound_map = {"SOFT": 0, "MEDIUM": 1, "HARD": 2, "INTERMEDIATE": 3, "WET": 4}
                compound = compound_map.get(compound_str, 5)
                tyre_life = int(lap["TyreLife"]) if not pd.isna(lap["TyreLife"]) else 0

                # Pitstop info
                stint = int(lap["Stint"]) if not pd.isna(lap["Stint"]) else 1
                pitstops = stint - 1
                
                # Lap PB so far (including this lap if accurate)
                if lap["IsAccurate"] and lap_duration > 0:
                    p_best_lap = min(p_best_lap, lap_duration)

                driver_data.append(
                    (race_time, start_position, end_position, lap_duration, compound, tyre_life, pitstops, p_best_lap))
                
                # Sector info
                s1_time = lap["Sector1Time"]
                s2_time = lap["Sector2Time"]
                s3_time = lap["Sector3Time"]
                
                s1_end = lap["Sector1SessionTime"].total_seconds() - self.race_start_offset if not pd.isna(lap["Sector1SessionTime"]) else None
                s2_end = lap["Sector2SessionTime"].total_seconds() - self.race_start_offset if not pd.isna(lap["Sector2SessionTime"]) else None
                s3_end = lap["Sector3SessionTime"].total_seconds() - self.race_start_offset if not pd.isna(lap["Sector3SessionTime"]) else None

                def get_color(val, p_best, g_best):
                    if pd.isna(val): return 0
                    if val <= g_best: return 3 # Purple
                    if val <= p_best: return 2 # Green
                    return 1 # Yellow

                s1_color = get_color(s1_time, p_best_s1, global_best_s1)
                s2_color = get_color(s2_time, p_best_s2, global_best_s2)
                s3_color = get_color(s3_time, p_best_s3, global_best_s3)

                # Update personal bests for NEXT lap
                if not pd.isna(s1_time) and s1_time < p_best_s1: p_best_s1 = s1_time
                if not pd.isna(s2_time) and s2_time < p_best_s2: p_best_s2 = s2_time
                if not pd.isna(s3_time) and s3_time < p_best_s3: p_best_s3 = s3_time

                sector_data.append({
                    "s1_end": s1_end,
                    "s2_end": s2_end,
                    "s3_end": s3_end,
                    "s1_color": s1_color,
                    "s2_color": s2_color,
                    "s3_color": s3_color
                })
                
                prev_position = end_position

            driver_data.sort(key=lambda x: x[0])
            self.race_data[code] = {
                "times": [t for t, _, _, _, _, _, _, _ in driver_data],
                "positions": [sp for _, sp, _, _, _, _, _, _ in driver_data],
                "end_positions": [ep for _, _, ep, _, _, _, _, _ in driver_data],
                "durations": [d for _, _, _, d, _, _, _, _ in driver_data],
                "compounds": [c for _, _, _, _, c, _, _, _ in driver_data],
                "tyre_lives": [tl for _, _, _, _, _, tl, _, _ in driver_data],
                "pitstops": [ps for _, _, _, _, _, _, ps, _ in driver_data],
                "personal_bests": [pb for _, _, _, _, _, _, _, pb in driver_data],
                "sectors": sector_data,
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

    def get_session_status(self, race_time):
        if not self.track_status_data:
            return "green"
        
        idx = bisect.bisect_right([t for t, s in self.track_status_data], race_time) - 1
        if idx < 0:
            raw_status = self.track_status_data[0][1]
        else:
            raw_status = self.track_status_data[idx][1]
            
        # Map status to color strings
        if raw_status == '1':
            return "green"
        elif raw_status in ['2', '4', '6', '7']:
            return "yellow"
        elif raw_status == '5':
            return "red"
        return "green"

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

    def _get_lap_progress(self, driver_data, race_time):
        """Bereken voortgang in huidige ronde als percentage (0-100)."""
        times = driver_data["times"]
        durations = driver_data["durations"]
        if not times:
            return 0.0

        idx = bisect.bisect_right(times, race_time) - 1
        if idx < 0:
            return 0.0
        if idx >= len(times):
            idx = len(times) - 1

        lap_start = times[idx]
        lap_dur = durations[idx] if durations[idx] > 0 else 80.0
        elapsed = race_time - lap_start
        fraction = min(elapsed / lap_dur, 1.0)
        return fraction * 100.0

    def get_state_at(self, race_time):
        drivers = {}
        for code, data in self.race_data.items():
            lap_progress = self._get_lap_progress(data, race_time)
            
            # Determine current sector colors with "lingering" logic
            s1_c, s2_c, s3_c = 0, 0, 0
            if data["times"]:
                idx = bisect.bisect_right(data["times"], race_time) - 1
                if idx >= 0:
                    curr_sect = data["sectors"][idx] if idx < len(data["sectors"]) else None
                    prev_sect = data["sectors"][idx-1] if idx > 0 else None
                    
                    # S1: show current if passed, else previous
                    if curr_sect and curr_sect["s1_end"] and race_time >= curr_sect["s1_end"]:
                        s1_c = curr_sect["s1_color"]
                    elif prev_sect:
                        s1_c = prev_sect["s1_color"]
                        
                    # S2: show current if passed, else previous
                    if curr_sect and curr_sect["s2_end"] and race_time >= curr_sect["s2_end"]:
                        s2_c = curr_sect["s2_color"]
                    elif prev_sect:
                        s2_c = prev_sect["s2_color"]
                        
                    # S3: show current if passed (unlikely during lap), else previous
                    if curr_sect and curr_sect["s3_end"] and race_time >= curr_sect["s3_end"]:
                        s3_c = curr_sect["s3_color"]
                    elif prev_sect:
                        s3_c = prev_sect["s3_color"]

            if not data["times"]:
                grid_pos = self.driver_info.get(code, {}).get("grid_position", 99)
                drivers[code] = {
                    "official_position": grid_pos,
                    "number": self.driver_info.get(code, {}).get("number", 0),
                    "color": self.driver_info.get(code, {}).get("color", 16777215),
                    "interval": 0.0,
                    "lap_progress": 0.0,
                    "total_progress": -1.0,  # DNF of niet gestart
                    "s1_color": 0, "s2_color": 0, "s3_color": 0,
                    "compound": 5, "tyre_life": 0, "pitstops": 0,
                    "last_lap_time": 0.0, "personal_best": 0.0
                }
            else:
                idx = bisect.bisect_right(data["times"], race_time)
                if idx == 0:
                    # Voor de eerste ronde - gebruik grid positie
                    grid_pos = self.driver_info.get(code, {}).get("grid_position", 99)
                    drivers[code] = {
                        "official_position": grid_pos,
                        "number": self.driver_info.get(code, {}).get("number", 0),
                        "color": self.driver_info.get(code, {}).get("color", 16777215),
                        "interval": 0.0,
                        "lap_progress": lap_progress,
                        "total_progress": 0.0 + (lap_progress / 100.0),
                        "s1_color": s1_c, "s2_color": s2_c, "s3_color": s3_c,
                        "compound": data["compounds"][0] if data["compounds"] else 5,
                        "tyre_life": data["tyre_lives"][0] if data["tyre_lives"] else 0,
                        "pitstops": data["pitstops"][0] if data["pitstops"] else 0,
                        "last_lap_time": 0.0,
                        "personal_best": 0.0
                    }
                else:
                    off_pos = data["positions"][idx - 1]
                    # Totale progressie = aantal voltooide ronden + voortgang in huidige ronde
                    total_progress = (idx - 1) + (lap_progress / 100.0)
                    
                    last_lap_t = 0.0
                    if idx > 1: # We are at least in Lap 2, so Lap 1 (idx 0) is finished
                        last_lap_t = data["durations"][idx - 2]
                    
                    pb_t = data["personal_bests"][idx - 1]
                    if pb_t == float('inf'): pb_t = 0.0

                    drivers[code] = {
                        "official_position": off_pos,
                        "number": self.driver_info.get(code, {}).get("number", 0),
                        "color": self.driver_info.get(code, {}).get("color", 16777215),
                        "interval": 0.0,
                        "lap_progress": lap_progress,
                        "total_progress": total_progress,
                        "s1_color": s1_c, "s2_color": s2_c, "s3_color": s3_c,
                        "compound": data["compounds"][idx - 1],
                        "tyre_life": data["tyre_lives"][idx - 1],
                        "pitstops": data["pitstops"][idx - 1],
                        "last_lap_time": last_lap_t,
                        "personal_best": pb_t
                    }

        # Sorteer coureurs op basis van total_progress (aflopend)
        if race_time < 10.0:
            sorted_drivers_list = sorted(
                drivers.items(), 
                key=lambda x: x[1]["official_position"]
            )
        else:
            sorted_drivers_list = sorted(
                drivers.items(), 
                key=lambda x: (-x[1]["total_progress"], x[1]["official_position"])
            )

        # Nieuwe posities toewijzen op basis van de volgorde in de lijst
        for i, (code, _) in enumerate(sorted_drivers_list):
            if drivers[code]["total_progress"] < -0.5: # DNF
                drivers[code]["position"] = 99
            else:
                drivers[code]["position"] = i + 1

        # Intervallen berekenen
        prev_driver_code = None
        for code, _ in sorted_drivers_list:
            if drivers[code]["position"] == 99:
                continue

            if prev_driver_code is None:
                drivers[code]["interval"] = 0.0
            else:
                track_pos, _ = self._get_track_position(self.race_data[code], race_time)
                ahead_data = self.race_data[prev_driver_code]
                target_lap_idx = int(track_pos)
                interval = 0.0
                if target_lap_idx < len(ahead_data["durations"]):
                    ahead_dur = ahead_data["durations"][target_lap_idx]
                    if ahead_dur > 0:
                        target_time = ahead_data["times"][target_lap_idx] + (track_pos % 1) * ahead_dur
                        interval = race_time - target_time
                drivers[code]["interval"] = round(max(0.0, interval), 3)

            prev_driver_code = code

        return drivers


class OSCBridge:
    def __init__(self, ip=None, port=7001):
        if ip is None:
            ip = os.getenv("OSC_IP", "127.0.0.1")
        self.client_osc = udp_client.SimpleUDPClient(ip, port)
        self.client_strings = udp_client.SimpleUDPClient(ip, 7002)
        self.client_status = udp_client.SimpleUDPClient(ip, 7003)

    def send_session_time(self, race_time):
        self.client_osc.send_message("/session/time", race_time)

    def send_session_status(self, status):
        self.client_status.send_message("/session/status", status)

    def send_driver(self, position, driver_code, number, color, interval, lap_progress, s1_c, s2_c, s3_c, compound, tyre_life, pitstops, last_lap_time, pb_lap_time):
        self.client_osc.send_message(f"/p{position}/code", driver_code)
        self.client_osc.send_message(f"/p{position}/number", number)
        self.client_osc.send_message(f"/p{position}/color", color)
        self.client_osc.send_message(f"/p{position}/interval", interval)
        self.client_osc.send_message(f"/p{position}/lap_progress", lap_progress)
        self.client_osc.send_message(f"/p{position}/s1_color", s1_c)
        self.client_osc.send_message(f"/p{position}/s2_color", s2_c)
        self.client_osc.send_message(f"/p{position}/s3_color", s3_c)
        self.client_osc.send_message(f"/p{position}/tyre/compound", compound)
        self.client_osc.send_message(f"/p{position}/tyre/life", tyre_life)
        self.client_osc.send_message(f"/p{position}/pitstops", pitstops)
        self.client_osc.send_message(f"/p{position}/lap/last", last_lap_time)
        self.client_osc.send_message(f"/p{position}/lap/best", pb_lap_time)

    def send_batch(self, drivers, race_time):
        self.send_session_time(race_time)
        sorted_drivers = sorted(drivers.items(), key=lambda x: x[1]["position"])
        for code, data in sorted_drivers:
            self.send_driver(data["position"], code,
                             data["number"], data["color"], data["interval"], data["lap_progress"],
                             data["s1_color"], data["s2_color"], data["s3_color"],
                             data["compound"], data["tyre_life"], data["pitstops"],
                             data["last_lap_time"], data["personal_best"])

    def send_lap_info(self, current_lap, total_laps):
        self.client_osc.send_message("/race/lap/current", current_lap)
        self.client_osc.send_message("/race/lap/total", total_laps)

    def send_abbr_batch(self, sorted_drivers):
        abbr_list = [code for code, data in sorted_drivers]
        abbr_str = ",".join(abbr_list)
        self.client_strings.send_message("/race/abbreviations", abbr_str)


class PlaybackEngine:
    def __init__(self, year=2026, round=4, session_type="R", speed=1.0, tick_rate=1.0):
        self.clock = RaceClock(speed_multiplier=speed)
        self.data_engine = DataEngine()
        self.osc = OSCBridge(port=7001)
        self.tick_rate = tick_rate
        self.year = year
        self.round = round
        self.session_type = session_type
        self.running = True
        self.input_thread = None

    def setup(self):
        self.data_engine.load_session(self.year, self.round, self.session_type)
        self.input_thread = threading.Thread(target=self.handle_input, daemon=True)
        self.input_thread.start()

    def handle_input(self):
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == "start": self.clock.start()
                elif cmd == "pause": self.clock.pause()
                elif cmd == "quit": self.running = False
            except EOFError: break

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
                session_status = self.data_engine.get_session_status(race_time)
                self.osc.send_session_status(session_status)
                state = self.data_engine.get_state_at(race_time)
                self.osc.send_batch(state, race_time)
                leader_code = next((c for c, d in state.items() if d["position"] == 1), None)
                current_lap = 0
                if leader_code and leader_code in self.data_engine.race_data:
                    leader_times = self.data_engine.race_data[leader_code]["times"]
                    current_lap = bisect.bisect_right(leader_times, race_time)
                self.osc.send_lap_info(current_lap, self.data_engine.total_laps)
                sorted_state = sorted(state.items(), key=lambda x: x[1]["position"])
                self.osc.send_abbr_batch(sorted_state)
                top5 = [f"{code}=P{data['position']}" for code, data in sorted_state[:5] if data['position'] != 99]
                print(f"\rTijd: {race_time:.1f}s | Status: {session_status} | Top 5: {', '.join(top5)}", end="", flush=True)
            time.sleep(self.tick_rate)
        self.cleanup()

    def cleanup(self):
        self.running = False
        print("\nPlayback gestopt")


if __name__ == "__main__":
    engine = PlaybackEngine(year=2026, round=4, session_type='R', speed=1.0, tick_rate=1.0)
    engine.setup()
    engine.run()
