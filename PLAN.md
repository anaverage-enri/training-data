# Training Plan — Ironman 70.3 Da Nang

The plan from 28 Oct 2026 to race day, Sunday 9 May 2027. The 70.3 is the A race. The Galaxy Run
on 22 Nov is a goal race inside the plan. Weeks run Monday to Sunday, and W0 starts Monday 26 Oct.

Each review checks the past week against this plan and the guardrails at the end. The plan
changes when the data says it should, and every change goes in `LOG.md`.

---

## Where you stand (28 Oct 2026)

**Recovery.** Still STRAINED.
- 7-day HRV is 44 ms, below the 48–63 ms baseline (LOW).
- Readiness was 1–29 from 22 to 27 Oct and 49 on 28 Oct.
- The load came from three things in a row: the half on 18 Oct, the 150 km ride on 25 Oct after
  2.8 h of sleep, and badminton on 26 Oct.
- At FTP 152 W, the 150 km ride was IF 0.69 and TSS ≈ 289. The table says 0.52 and 167 because
  the Edge computes against a 200 W placeholder. The watch uses about 162 W.

**Run** (since June).
- Volume: 25–37 km a week since August. Easy runs go 8:00–8:40/km at HR ~150.
- Intensity: since 31 Aug only 33 % of run time was in Z0–2; 35 % was in Z3 and 32 % in Z4–5.
  Long runs sat mostly in Z3. Too much running is moderately hard. This is the main thing to
  change.
- The "HMP" sessions (3×2 km) were run at 5:21–5:55/km at HR 178–187. That is 5K–10K effort,
  not half-marathon pace. Realistic HMP today is 6:20–6:30/km.
- 10K on 1 Oct, HR-capped: 64:21 (6:37 then 6:15, at HR 176 then 181). The Riegel formula turns
  that into about 2:22 for a half. Garmin predicted 2:11 on the morning of 18 Oct; the result
  was 2:25:57.

**Bike** (since 27 Sep).
- FTP 152 W (2.45 W/kg) is Garmin's estimate. It has never been tested, and the best 20 minutes
  so far is 121 W.
- Cadence is 55–73 rpm. 81 % of ride time is easy.

**Swim.**
- Freestyle: 50–200 m continuous.
- Breaststroke: about 1:55–2:55/100 m.
- The watch logs at most one freestyle length per lesson, so lesson data cannot track freestyle.

**Sleep.**
- Average bedtime is 23:08–01:16 on every night of the week, not just after lessons.
- Wake-up is about 07:30 when nothing starts early.
- Before early starts: 4.6 h on Saturday nights, 5.4–6.0 h on weeknights.

---

## Targets

### Galaxy Run, Sunday 22 Nov

**Target: 2:15–2:18.**
- Sub-2:15 is possible on a good day with the pacing below.
- Sub-2:10 (6:10/km) is out of reach this time: the 10K says about 2:22, and no training run has
  gone past 18 km.
- Whatever the clock says, success is even pacing, no cramps, and a PB under 2:25:57.

| km | Pace | HR cap |
|---|---|---|
| 1–5 | 6:35–6:40 | ≤ 175 |
| 6–15 | 6:20–6:25 | ≤ 182 |
| 16–21.1 | hold it; from km 18, race what is left | — |

- On 18 Oct, HR was 182–189 on km 2–8. Keep the first 5 km under the cap even if it feels slow.
- Projection: 32:55 + 63:40 + 38:07 at 6:15/km = 2:14:42.
- **Fallback:** if HR is above 178 at 6:35 by km 4 (heat, a short night), run 6:30–6:35 to
  km 18, then push. That lands around 2:18.

**Fuel:**
- Breakfast 2.5–3 h before the start: about 100 g of carbohydrate, food you know.
- A gel 10 min before the start, then gels at about 35, 70 and 105 min.
- Electrolyte drink at the aid stations, for 300–600 mg of sodium an hour.
- Rehearse all of it on 8 and 15 Nov.

**Sleep:** Friday 20 Nov is the night that counts, so skip or shorten the lesson. Lights-out
around 20:30 on Saturday.

### Ironman 70.3 Da Nang, Sunday 9 May

The course:
- **Swim:** one lap in the sea at Son Thuy beach, 26–28 °C water, so no wetsuits. The beach has a
  shore break.
- **Bike:** two flat laps with two bridges and a headwind on the way back.
- **Run:** flat along the coast, with no shade. Reports put it at 35–40 °C.

In 2023, about 59 % of finishers went under 7:00.

| | Sub-7:00 line | Sub-6:30 line |
|---|---|---|
| Swim 1.9 km, with beach entry and exit | 52:00 (~2:40/100 m) | 47:00 (~2:24/100 m) |
| T1 | 6:00 | 5:00 |
| Bike 90 km | 3:10:00 (28.4 km/h, ~120 W on aero bars) | 3:02:00 (29.7 km/h, ~133 W on aero bars) |
| T2 | 4:00 | 3:00 |
| Run 21.1 km | 2:45:00 (7:49/km, aid stations walked) | 2:32:00 (7:12/km) |
| **Total** | **6:57:00** | **6:29:00** |

**The run is the leg most likely to break sub-7.** Running 2:45 in 35–40 °C after the bike needs a
fresh pace of about 6:45/km at HR 165–170. Today it is about 6:57: the last 12 km of the 27 Sep
long run, at HR 168 and 25 °C.

**The bike is the leg you can bank**, once the aero bars are on. The model below is calibrated on
the 150 km ride: it predicts 24.9 km/h, and the ride averaged 24.6.

| Power | Aero bars | Hoods |
|---|---|---|
| 115 W | 3:13 | 3:25 |
| 125 W | 3:07 | 3:18 |
| 135 W | 3:01 | 3:13 |

It assumes CdA 0.33 on the hoods and 0.27 on aero bars, 73 kg of rider and bike, and 5 % added
for the headwind, the bridges and the U-turns.

**What each line needs by mid-March:**
- **Sub-7:00:**
  - aero bars and FTP ≥ 160 W, for a race power of about 118–122 W
  - 1,500 m of continuous freestyle
  - a fresh half of about 2:15, and the Galaxy Run is the first read
  - long-run pace at HR 150–155 improving to about 7:30/km (morning, feels-like ≤ 30 °C)
  - 18 km long runs without cramps
- **Sub-6:30:**
  - FTP ≥ 175 W
  - CSS ≤ 2:15/100 m
  - a fresh half around 2:05
  - long-run pace at HR 150–155 about 7:00/km

**Race execution:**
- Bike at 72–76 % of tested FTP (IF 0.72–0.76), with bike HR ≤ ~152 and ≤ 95 % FTP on the
  bridges. Cadence 85–90.
- Run the first 5 km at HR ≤ 162, then hold HR ≤ 170. Walk every aid station for ice, sponges
  and fuel.
- The final power and run caps are set at the W19 review and checked on the 4 Apr simulation.

---

## The season

- **Hours** include the two lessons, about 3 h a week.
- **Long ride:** Sunday from 04:30, with a brick run straight after.
- **Long run:** Saturday from about 06:30. It means N km or 2:15, whichever comes first; in heat
  the clock ends the run, not the distance. It stays at HR ≤ 157 except for planned segments.
- **Race power** is 72–76 % of FTP. **70.3 effort** is HR 160–168.

| Wk | Monday | Phase | h | Long ride + brick | Long run | Notes |
|---|---|---|---|---|---|---|
| 0 | 26 Oct | Absorb | ~7 | — | Sun 1 Nov: 12 km easy | easy only |
| 1 | 2 Nov | Galaxy build | 10.5 | — (Tue/Fri 60–90 min) | Sun 8: **18 km rehearsal** | |
| 2 | 9 Nov | Galaxy build | 10.5 | — | Sun 15: 15 km, 6 at HMP | |
| 3 | 16 Nov | Taper + race | 6.5 | — | **Sun 22: Galaxy Run** | |
| 4 | 23 Nov | Recover + test | 8 | Sun 29: FTP test + 10 min | — | Sat 28: swim benchmark |
| 5 | 30 Nov | Base 1 | 12 | 2:15 + 10 | 13 km | aero bars fitted |
| 6 | 7 Dec | Base 1 | 12.5 | 2:30 + 10 | 14 km | |
| 7 | 14 Dec | Base 1 | 13 | 2:45 + 10 | 15 km | |
| 8 | 21 Dec | Recovery | 8.5 | 2:00 easy | 10 km | Sat 26: 400 m continuous |
| 9 | 28 Dec | Base 2 | 12.5 | 2:45 + 15 | 15 km | Fri 1 Jan: 2:00 ride |
| 10 | 4 Jan | Base 2 | 13 | 3:00 + 15 | 16 km | |
| 11 | 11 Jan | Base 2 | 13.5 | 3:00 + 15, 2×20 min at 76–80 % | 16 km | Sat 16: 800 m continuous |
| 12 | 18 Jan | Recovery + tests | 9 | Sun 24: **sea trip 1** + 1:30 easy | 10 km | Tue 19 FTP, Sat 23 CSS |
| 13 | 25 Jan | Build | 13.5 | 3:15 + 20, 2×30 min race power | 17 km, last 3 at 70.3 effort | |
| 14 | 1 Feb | Build / Tết | 12 | Fri 5 (holiday): 3:15 + 20 | Thu 4 (holiday): 17 km | Sat 6–Sun 7: family |
| 15 | 8 Feb | Tết recovery | 8 | Tue 9 (holiday): 2:00; Sun 14: 2:30 | Sat 13: 12 km | holiday to Wed 10 |
| 16 | 15 Feb | Build | 13.5 | 3:15 + 20, 2×40 min race power | 17 km, last 4 at 70.3 | Sat 20: 1,200 m continuous |
| 17 | 22 Feb | Build | 14 | 3:30 + 25, 3×30 min race power | 18 km, last 5 at 70.3 | |
| 18 | 1 Mar | Build | 14.5 | 3:30 + 30, 2×45 min race power | 18 km, 3×3 km at 70.3 | Sat 6: 1,500 m continuous |
| 19 | 8 Mar | Recovery + tests | 9 | Sun 14: **sea trip 2** + 2:00 on the coast | 10 km | Tue 9 FTP, Sat 13 CSS, **swim decision** |
| 20 | 15 Mar | Specific | 14 | 3:30 + 30, 90 min race power | 18 km, last 6 at 70.3 | |
| 21 | 22 Mar | Specific | 14.5 | 3:45 + 40, 2×50 min race power | 18 km (19 if all green) | |
| 22 | 29 Mar | Specific | 14.5 | **Simulation Sun 4 Apr:** 90 km race power + 60 min run | Sat 3: 1.9 km sea swim | **sea trip 3**, Vũng Tàu |
| 23 | 5 Apr | Recovery | 9 | 2:30 easy | 12 km | |
| 24 | 12 Apr | Specific | 14 | Sun 18: 3:30, 2×45 min race power + 40 min run | Sat 17: 14 km + 2,000 m swim | home simulation |
| 25 | 19 Apr | Specific (−15 %) | 12 | 3:00 + 20, 60 min race power | 16 km, last 5 at 70.3 | |
| 26 | 26 Apr | Taper | 8.5 | Sun 2 May: 2:00 + 15, 2×15 min race power | Sat 1 May: 12 km | Fri 30 Apr: optional sea swim |
| 27 | 3 May | Race week | 5 + race | Tue 4: 1:00, 3×5 min race power | — | travel Thu 6; **race Sun 9** |

- **Pattern:** 3 weeks building, then a recovery week at about 60–65 % of the week before. The
  tests go in the recovery weeks.
- **Taper:** about 40 % less volume in W26 and 65 % less in W27, keeping intensity and frequency
  (Bosquet 2007).
- **Long-run limit:** no long run is more than 10 % longer than the longest run of the previous
  30 days. The Galaxy Run itself is the one exception (Frandsen 2025).
- **Tết:** the 4–10 Feb holiday is still a proposal. If the official days differ, put W14's long
  run and long ride on the first two holiday days, and keep mùng 1–3 (Sat 6–Mon 8 Feb) for
  family. If you travel without the bike, swap the rides for runs and swims.
- **Too much in a week?** Peak weeks reach 14–14.5 h. Drop in this order:
  1. the optional Tuesday run
  2. strength B
  3. shorten the Friday ride
  4. take 30 min off the long ride

---

## The week

| Day | Morning | Evening | Lights-out |
|---|---|---|---|
| Mon | rest | **strength A**, in the old badminton slot | 22:00 |
| Tue | **bike quality**, 04:45–06:15 | optional easy run, 25–35 min (from Base 2, only when HRV is in range) | 23:00 |
| Wed | — | swim lesson | ~23:00 |
| Thu | sleep in | **run quality** at ~18:30, then strength B | 22:00 |
| Fri | easy ride, 04:45–06:00 | swim lesson | ~23:00 |
| Sat | **long run**, from ~06:30 | own swim, 45–60 min | 21:30 |
| Sun | **long ride** from 04:30 + brick run | 20–30 min nap | 23:00 |

- Three early starts a week: Tuesday, Friday and Sunday. No early start the morning after a
  lesson night.
- The lights-out times are part of the plan. The early starts only work with them.
- There is no Wednesday run because the lesson takes the evening.
- The Saturday run starts at 06:30 rather than mid-morning to keep the time in the heat down.
- Saturday afternoon is the default for the third swim. Move it to any day the pool suits.
- If the feels-like temperature is above 35 °C at 18:30, start Thursday's run at 19:30 and cut
  the hard part by a third.
- Badminton pauses until after 9 May. It was the one high-impact, side-to-side, Z4–Z5 session of
  the week, and it landed the day after the long session.

**When the trainer arrives:**
- Tuesday's bike quality moves to about 19:00 indoors, with a 10–15 min run straight after.
  Tuesday morning becomes a sleep-in, which leaves two early starts.
- From Build, an optional 30–45 min easy spin goes on Thursday.
- FTP tests move indoors.
- Note the date in `ATHLETE.md`.

**If the lessons stop:** two structured 60-min swims on Wednesday and Friday evenings take their
place.

---

## Sessions by phase

**Bike targets** are a share of FTP, 152 W until the test on 29 Nov:

| Zone | % FTP | Watts at 152 W |
|---|---|---|
| Z2 | 56–75 % | 85–114 W |
| Tempo | 76–87 % | 116–132 W |
| Sweet spot | 88–93 % | 134–141 W |
| Threshold | 95–100 % | 144–152 W |
| Race power | 72–76 % | 109–116 W |

**Run zones** are Garmin's: Z2 143–157, Z3 158–172, Z4 173–187.

| Phase | Tue bike quality | Fri ride | Thu run quality (by HR in heat) | Sat own swim | Strength |
|---|---|---|---|---|---|
| Galaxy, W1–3 | 75–90 min Z2 + 6×1 min at 95–105 rpm | 60–75 min Z2 | W1 3×2 km, W2 2×4 km at 6:20–6:28 (HR ≤ 182); W3 2×1 km | drills from the lessons + 8–12×25 m freestyle | current routine on Mon (push-ups, squats, ~15 min); B bodyweight, 2 sets, on Thu; none in W3 |
| Base 1, W5–7 | 1:15: 3×10 min tempo at 80–90 rpm + 6×1 min spin-ups | 1:00 Z2; first rides on the aero bars | 8×30–45 s uphill on bridge ramps; W7 6×2 min at 10K effort | 12–16×50 m → 6×100 m; add 50–100 m to one continuous swim each week | A 45 min + B 20 min |
| Base 2, W9–11 | 1:30: sweet spot 3×12 → 3×15 → 2×20 min | 1:00 Z2 on the bars | 3×8 → 3×10 → 4×10 min at HR 173–180 | 4×200 m → continuous 600–800 m | A 45 + B 20 (add pogo hops and skips) |
| Build, W13–18 | 1:30: threshold 4×8 → 3×10 → 2×15 → 2×20 min | 1:15 with 2×15 min at race power | tempo 2×15 → 25 → 30 min at HR 170–178; every other week 5×1 km at 10K effort | CSS sets 8–10×100 m at CSS + 5 s; 3×400 m with sighting; continuous 1,000 → 1,500 m | A 40 (3×5–6) + B 10 |
| Specific, W20–25 | 1:30: 3×20 min at race power + 5×1 min at 110 % for the bridges | 1:15–1:30 with 30 min at race power | 30–40 min at 70.3 effort, or 3×10 min at threshold | 2,000 m continuous with sighting; 4×400 m at race pace; no push-offs from the wall | A 30–40 (2×5) |
| Taper, W26–27 | 1:00 with 3×8 min at race power | 45–60 min easy | 4×5 min at 70.3 effort | 1,500 m with 6×100 m at race pace | one short A in W26 |

**Strength A** (Monday, gym), from 30 Nov. Leave 2–3 reps in reserve.
- squat or leg press, 3–4×5–8
- Romanian deadlift, 3×6–8
- Bulgarian split squat, 3×6–8 per leg
- calf raises, slow on the way down: straight knee 3×10–12, bent knee 3×12–15
- pull-up or lat pulldown, 3×6–10
- push-up or bench press, 3×8–12
- Pallof press, side plank, dead bug

Keep the loads moderate for the first three weeks, so Tuesday's ride is not sore.

**Strength B** (Thursday, after the run):
- single-leg RDL
- step-ups
- single-leg calf raises
- band hip abduction
- Copenhagen plank
- swim-cord pulls

**Recovery weeks:**
- Long ride 2:00–2:30 easy, long run 10–12 km.
- Tests replace the intervals.
- Strength A drops to 2 sets.

**Sea trips (Vũng Tàu):**
- January: first open water, 3×10–15 min.
- March: 2×1,000 m.
- April: the race simulation.
- Optional: 30 Apr, a holiday.
- Always swim with a buddy and a tow float, at the calmest hour.

**Swim milestones** (continuous freestyle):

| Date | Milestone |
|---|---|
| Sat 26 Dec | 400 m |
| Sat 16 Jan | 800 m |
| Sat 20 Feb | 1,200 m |
| Sat 6 Mar | 1,500 m |
| early April | 2,000 m in the pool |
| Sat 3 Apr | 1.9 km in the sea |

**Swim decision, Sunday 14 Mar:**
- **1,500 m continuous done:** race in freestyle.
- **Not yet:** race freestyle with planned breaststroke breaks, for example 200 m freestyle and
  50 m breaststroke. Any stroke is legal, and freestyle keeps building until race day.
- **The cutoff is safe either way:** breaststroke alone at 2:30–2:50/100 m in the sea is about
  48–54 min, and the usual 70.3 swim cutoff is 1:10.

---

## Galaxy block, day by day

### W0, 26 Oct–1 Nov: absorb
Easy only. The one early start is Sunday's easy run.

| Day | Session |
|---|---|
| Mon 26 | badminton (done) |
| Tue 27 | 5 km easy (done): 8:00/km at HR 156, 35 °C feels-like |
| Wed 28 | lesson (done) |
| Thu 29 | rest; a 20–30 min walk |
| Fri 30 | sleep in, no ride; lesson in the evening |
| Sat 31 | 40 min easy at HR ≤ 155, around 07:00; lights-out 21:30 |
| Sun 1 | 12 km at HR ≤ 157, from 05:00 |

On Sunday 1 Nov, if that morning's readiness is below 25 or 7-day HRV is still at 44 or lower,
run 8 km instead.

### W1, 2–8 Nov

| Day | Session |
|---|---|
| Mon 2 | current routine: push-ups and squats, ~15 min (strength A starts 30 Nov) |
| Tue 3 | 75 min Z2 (HR ≤ 147) with 6×1 min at 95–105 rpm |
| Wed 4 | lesson |
| Thu 5 | 15 min easy, 3×2 km at 6:20–6:28 (HR ≤ 182) with 2 min jog, 10 min easy; then B, bodyweight, 2 sets |
| Fri 6 | 60–75 min Z2; lesson |
| Sat 7 | 35 min easy + 6×20 s strides; own swim #1; lights-out 21:00 |
| Sun 8 | **dress rehearsal** |

**Dress rehearsal, Sunday 8 Nov:**
- Start at the race start time, or 04:30 if it is not published yet.
- 18 km or 2:15: 12 km at HR ≤ 157, then 5 km at 6:22–6:30, then 1 km easy. If the easy part runs
  long, shorten it and keep the 5 km.
- Race breakfast, race shoes and race kit. A gel 10 min before, then gels at 35, 70 and 105 min.
- Write down everything you eat and drink.

### W2, 9–15 Nov

| Day | Session |
|---|---|
| Mon 9 | current routine, ~15 min |
| Tue 10 | 75–90 min Z2 with spin-ups |
| Wed 11 | lesson |
| Thu 12 | 15 min easy, 2×4 km at 6:20–6:25 (HR ≤ 182) with 3 min jog, 10 min easy; then B, bodyweight |
| Fri 13 | 60 min Z2; lesson |
| Sat 14 | 35–40 min easy + strides; own swim #2 |
| Sun 15 | 15 km from 04:30: 8 easy, 6 at 6:20–6:25, 1 easy; second fuel rehearsal |

### W3, 16–22 Nov

| Day | Session |
|---|---|
| Mon 16 | rest + mobility |
| Tue 17 | 60 min easy with 3×2 min brisk |
| Wed 18 | lesson, easy |
| Thu 19 | 7 km: 3 easy, 2×1 km at 6:20, 2 easy |
| Fri 20 | sleep in; skip or shorten the lesson; lights-out 22:00 |
| Sat 21 | 20 min shakeout + 4 strides; bib pickup at SECC; carbohydrate-rich meals you know (6–8 g/kg); lights-out ~20:30 |
| Sun 22 | **Galaxy Run** |

### W4, 23–29 Nov

| Day | Session |
|---|---|
| Mon 23 | rest |
| Tue 24 | optional 45 min spin |
| Wed 25 | lesson |
| Thu 26 | 30 min easy if nothing is sore |
| Fri 27 | 60 min Z2 with 3×1 min hard; lesson |
| Sat 28 | 30 min easy; **swim benchmark** in the afternoon |
| Sun 29 | **FTP test** at 05:00, then a 10 min jog |

---

## Tests

**FTP** on Sun 29 Nov, Tue 19 Jan and Tue 9 Mar.
- Warm up 20 min with 3×1 min fast, then 5 min hard, then 10 min easy.
- Then ride 20 min as hard as you can hold evenly. FTP is 95 % of the 20-min average.
- If you cannot get 20 uninterrupted minutes on a safe road at 05:00, do 2×8 min with 10 min easy
  between. FTP is then 90 % of the average of the two.
- **After every test, set FTP on the Edge 540, the watch and Garmin Connect.** Until then the IF
  and TSS in the table are wrong.

**Swim benchmark** on Sat 28 Nov:
- the longest continuous freestyle at an easy effort
- a 100 m freestyle time
- a 200 m breaststroke time

**CSS test** on Sat 23 Jan and Sat 13 Mar, once 400 m continuous is possible.
- 400 m time trial, 10 min easy, then a 200 m time trial.
- CSS per 100 m = (T400 − T200) / 2.

**Aerobic trend:** every review reads the pace at HR 150–155 over the first 30 min of the Saturday
long run, against `weather_feels_c`. It needs no extra session.

**Checkpoint at the W19 review (~14 Mar):** read the two split lines against FTP, CSS, continuous
swim and long-run HR. Then set race power and run caps.

---

## Guardrails

Read everything over 7-day windows.

- **HRV below the floor for 3+ days, or poor readiness:** if 7-day HRV is below the baseline floor
  (48 ms today) for 3+ days, or readiness is below 30 on 3 of the last 5 mornings, the next
  quality session goes easy and strength A drops to 2 sets.
- **Sustained strain:** if 7-day HRV is below the floor for 7+ days, or Garmin says STRAINED at
  two reviews in a row, start the recovery week now and shift the block by a week.
- **Short night:** under 5 h before an early start, do that session easy and shorter. Never pair
  two short nights with two quality sessions.
- **ACWR:** above 1.5, keep next week's hours flat.
- **Long runs:** none more than 10 % longer than the longest of the last 30 days.
- **Pain:** if it changes your stride or gets worse as you run, stop. Take 2 days without
  running, and see a physio if it lasts more than 3 days.
- **Zones:** at least 75 % of each week's run time in Z0–2. Long runs at HR ≤ 157 outside their
  planned segments.

---

## Fuel, heat, sleep, cramps

**Carbohydrate:**
- On the bike: 60 g an hour in Base 1, 75 g in Base 2, 90 g from Build. Use glucose and fructose
  products.
- Runs over 75 min: 30–60 g an hour.
- Every long session is gut training for race day (Jeukendrup).

**Sweat rate:**
- Weigh yourself nude before and after three long sessions in different heat.
- Sweat rate in L/h = (kg lost + litres drunk) / hours.
- Drink about 60–80 % of that.
- Start at about 500 mg of sodium an hour. Move toward 1,000 mg if your kit dries white.

**Heat:**
- The 70.3 run will happen around 10:30–13:00 in full sun.
- The Saturday long runs from 06:30 and the Sunday brick runs at 08:00–09:00 are the heat
  practice.
- Rehearse the race cooling: ice in the cap and the suit, cold sponges, cold drinks.

**Cramps:** in 210 Ironman triathletes, cramps went with earlier cramping and with running faster
than usual. They did not go with dehydration or blood sodium (Schwellnus 2011).
- The first fix is pacing and durability at race intensity.
- Fuel and sodium come second.
- Log every cramp with the km, the heat, the sleep and what you took.

**Sleep:**
- Keep the lights-out times in the week table, and nap on weekend afternoons.
- In race weeks, spend 8 h in bed Monday to Thursday.
- Reviews read sleep as a 7-day average. The 2021 consensus (Walsh) recommends an individual
  sleep plan rather than a fixed 7–9 h.

---

## Equipment and admin

- **Aero bars and a bike fit** by 30 Nov, so the position gets five months. Start on the bars on
  quiet roads and add aero time on the Friday ride. Note the date in `ATHLETE.md`: speed at the
  same power will step up.
- **FTP:** set it on every device after each test. The Edge uses 200 W today and the watch about
  162 W.
- **Own swims:** use the watch's drill mode for drills and kick, so freestyle lengths get counted.
- **To confirm:**
  - The Galaxy Run start time. It also sets the alarm for 8 Nov.
  - From the 70.3 athlete guide: the swim start format and time, the cutoffs, the aid-station
    products (train with them), the transition layout.
- **Race kit:** tri suit, race belt, elastic laces, cages for 2–3 bottles, a top-tube bag.

### Race week

| Day | Session |
|---|---|
| Mon 3 May | rest |
| Tue 4 | 1:00 with 3×5 min at race power |
| Wed 5 | 30 min with 3×3 min at 70.3 effort; lesson easy, or skip it |
| Thu 6 | travel to Da Nang; 20 min easy run |
| Fri 7 | 15–20 min sea swim on the course at race-start time; 30 min easy ride on the course |
| Sat 8 | 20 min spin + 10 min jog; bike and bag check-in; carbohydrate 8–10 g/kg; lights-out 20:30 |
| Sun 9 | **race** |

---

## Sources

**Race:**
- [moku.coach: IRONMAN 70.3 Da Nang review](https://moku.coach/race-ratings/70-3/ironman-703-danang/)
- [geeksonfeet: 2024 race report](https://geeksonfeet.com/race-reports/race-report-ironman-vietnam-2024/)
- [endurance-data: 2023 finish times](https://www.endurance-data.com/en/statistics/827-ironman-703-vietnam/)
- [Racecheck: reviews](https://racecheck.com/races/ironman-703-vietnam/)
- [IRONMAN wetsuit rules](https://www.slowtwitch.com/news/global-rule-standard-announced/)
- [Galaxy Run 2026](https://vm.vnexpress.net/galaxy-run-2-2026)
- [Tết 2027 date](https://thuvienphapluat.vn/hoi-dap-phap-luat/tet-nguyen-dan-2027-vao-ngay-nao-duong-lich-138080787.html)

**Training:**
- [Schwellnus 2011: cramps in 210 Ironman triathletes](https://bjsm.bmj.com/content/45/8/650)
- [Muñoz 2014: intensity distribution in an Ironman season](https://abacus.universidadeuropea.com/entities/publication/c7dad279-88e8-4a40-a281-307f24c5f006)
- [Frandsen 2025: single-run distance spikes and injury](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421110)
- [Bosquet 2007: taper meta-analysis](https://pubmed.ncbi.nlm.nih.gov/17762369/)
- [Jeukendrup: carbohydrate intake during exercise](https://www.mysportscience.com/post/2015/05/27/recommendations-for-carb-intake-during-exercise)
- [Rønnestad & Mujika 2014: strength training for running and cycling](https://www.inigomujika.com/en/2013/08/13/optimizing-strength-training-for-running-and-cycling-endurance-performance-a-review-2/3040/)
- [Walsh 2021: sleep and the athlete](https://bjsm.bmj.com/content/55/7/356.abstract)
- [Best Bike Split: 70.3 bike pacing](https://www.bestbikesplit.com/blog/pacing-70-3-bike-leg-intensity-factor-tss)
