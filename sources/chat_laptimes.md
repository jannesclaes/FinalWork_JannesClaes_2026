  ✓  ReadFile  app.py
  ✓  WriteFile  app.py → Accepted (+29, -12)

      172
      173           driver_data.sort(key=lambda x: x[0])
      174           self.race_data[code] = {
      175 -             "times": [t for t, _, _, _, _, _, _ in driver_data],
      176 -             "positions": [sp for _, sp, _, _, _, _, _ in driver_data],
      177 -             "end_positions": [ep for _, _, ep, _, _, _, _ in driver_data],
      178 -             "durations": [d for _, _, _, d, _, _, _ in driver_data],
      179 -             "compounds": [c for _, _, _, _, c, _, _ in driver_data],
      180 -             "tyre_lives": [tl for _, _, _, _, _, tl, _ in driver_data],
      181 -             "pitstops": [ps for _, _, _, _, _, _, ps in driver_data],
      175 +             "times": [t for t, _, _, _, _, _, _, _ in driver_data],
      176 +             "positions": [sp for _, sp, _, _, _, _, _, _ in driver_data],
      177 +             "end_positions": [ep for _, _, ep, _, _, _, _, _ in driver_data],
      178 +             "durations": [d for _, _, _, d, _, _, _, _ in driver_data],
      179 +             "compounds": [c for _, _, _, _, c, _, _, _ in driver_data],
      180 +             "tyre_lives": [tl for _, _, _, _, _, tl, _, _ in driver_data],
      181 +             "pitstops": [ps for _, _, _, _, _, _, ps, _ in driver_data],
      182 +             "personal_bests": [pb for _, _, _, _, _, _, _, pb in driver_data],
      183               "sectors": sector_data,
      184               "code": code
      185           }
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      293                   "lap_progress": 0.0,
      294                   "total_progress": -1.0,  # DNF of niet gestart
      295                   "s1_color": 0, "s2_color": 0, "s3_color": 0,
      295 -                 "compound": 5, "tyre_life": 0, "pitstops": 0
      296 +                 "compound": 5, "tyre_life": 0, "pitstops": 0,
      297 +                 "last_lap_time": 0.0, "personal_best": 0.0
      298               }
      299           else:
      300               idx = bisect.bisect_right(data["times"], race_time)
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      311                       "s1_color": s1_c, "s2_color": s2_c, "s3_color": s3_c,
      312                       "compound": data["compounds"][0] if data["compounds"] else 5,
      313                       "tyre_life": data["tyre_lives"][0] if data["tyre_lives"] else 0,
      312 -                     "pitstops": data["pitstops"][0] if data["pitstops"] else 0
      314 +                     "pitstops": data["pitstops"][0] if data["pitstops"] else 0,
      315 +                     "last_lap_time": 0.0,
      316 +                     "personal_best": 0.0
      317                   }
      318               else:
      319                   off_pos = data["positions"][idx - 1]
      320                   # Totale progressie = aantal voltooide ronden + voortgang in huidige ronde
      321                   total_progress = (idx - 1) + (lap_progress / 100.0)
      322 +                 
      323 +                 last_lap_t = 0.0
      324 +                 if idx > 1: # We are at least in Lap 2, so Lap 1 (idx 0) is finished
      325 +                     last_lap_t = data["durations"][idx - 2]
      326 +                 
      327 +                 pb_t = data["personal_bests"][idx - 1]
      328 +                 if pb_t == float('inf'): pb_t = 0.0
      329 + 
      330                   drivers[code] = {
      331                       "official_position": off_pos,
      332                       "number": self.driver_info.get(code, {}).get("number", 0),
      337                       "s1_color": s1_c, "s2_color": s2_c, "s3_color": s3_c,
      338                       "compound": data["compounds"][idx - 1],
      339                       "tyre_life": data["tyre_lives"][idx - 1],
      328 -                     "pitstops": data["pitstops"][idx - 1]
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      340 +                     "pitstops": data["pitstops"][idx - 1],
      341 +                     "last_lap_time": last_lap_t,
      342 +                     "personal_best": pb_t
      343                   }
      344
      345       # Sorteer coureurs op basis van total_progress (aflopend)
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      400   def send_session_status(self, status):
      401       self.client_status.send_message("/session/status", status)
      402
      389 - def send_driver(self, position, driver_code, number, color, interval, lap_progress, s1_c, s2_c, s3_c, compound, tyre_life, pitstops):
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      403 + def send_driver(self, position, driver_code, number, color, interval, lap_progress, s1_c, s2_c, s3_c, compound, tyre_life, pitstops,
          last_lap_time, pb_lap_time):
      404       self.client_osc.send_message(f"/p{position}/code", driver_code)
      405       self.client_osc.send_message(f"/p{position}/number", number)
      406       self.client_osc.send_message(f"/p{position}/color", color)
      412       self.client_osc.send_message(f"/p{position}/tyre/compound", compound)
      413       self.client_osc.send_message(f"/p{position}/tyre/life", tyre_life)
      414       self.client_osc.send_message(f"/p{position}/pitstops", pitstops)
      415 +     self.client_osc.send_message(f"/p{position}/lap/last", last_lap_time)
      416 +     self.client_osc.send_message(f"/p{position}/lap/best", pb_lap_time)
      417
      418   def send_batch(self, drivers, race_time):
      419       self.send_session_time(race_time)
      422           self.send_driver(data["position"], code,
      423                            data["number"], data["color"], data["interval"], data["lap_progress"],
      424                            data["s1_color"], data["s2_color"], data["s3_color"],
      409 -                          data["compound"], data["tyre_life"], data["pitstops"])
      ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
      425 +                          data["compound"], data["tyre_life"], data["pitstops"],
      426 +                          data["last_lap_time"], data["personal_best"])
      427
      428   def send_lap_info(self, current_lap, total_laps):
      429       self.client_osc.send_message("/race/lap/current", current_lap)

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ ✓  Shell python3 -m py_compile app.py                                                                                                                    │
│                                                                                                                                                          │
│                                                                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
  Lap Time Tracking Complete: Completed lap time tracking implementation.


✦ Ik heb de berekening van de persoonlijke snelste ronde en de laatste rondetijd toegevoegd.

  Wat er is aangepast:
   1. Preprocessing: Per coureur wordt nu tijdens het laden van de data bijgehouden wat hun "persoonlijke record" (PB) is tot aan elk moment in de race. Hierbij
      worden alleen "accurate" rondes (zonder fouten of onderbrekingen) meegerekend.
   2. Live State: Tijdens de playback wordt nu gekeken naar de laatst voltooide ronde om de last_lap_time te bepalen.
   3. OSC Addresses: De tijden worden (in seconden) verstuurd naar:
       * /p{position}/lap/last: De tijd van de vorige ronde.
       * /p{position}/lap/best: De snelste tijd van die coureur tot nu toe in de race.

  De waarden zijn 0.0 als er nog geen (accurate) ronde is voltooid. De syntax is gecontroleerd en de data-engine is bijgewerkt om deze extra velden efficiënt te
  verwerken.
