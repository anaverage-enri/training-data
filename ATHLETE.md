# Athlete Context

## Basic info
- Name: Enri
- Job: Software Engineer
- DOB: 25th October 1999
- Height: 164cm
- Weight: ~62kg

## Background
- **Badminton:** since September 2024, 4–5 sessions a week for two years. Cut back once running
  started: 20 sessions in June 2026, 2 in October. Paused from November until after the 70.3;
  the last session was 26th October.
- **Running:** since June 2026 (first logged run 31st May). Longest training run 18 km, on 30th
  August and 27th September.
- **Swimming:** breaststroke since secondary school. Learning freestyle, and will race the 70.3 in
  freestyle.
  - Freestyle: 50–200 m continuous on 28th October 2026.
  - Lessons every Wednesday and Friday evening in a 50 m pool. The breaststroke lengths in lesson
    data are the coach's warm-up, cool-down and drills.
  - One open-water swim so far: 500 m at Quy Nhơn, 12th August 2026.
- **Cycling:** bike bought 27th September 2026, first ride that evening. Longest ride 150 km, 25th
  October 2026.
- The Garmin record starts on 29th May 2026. Nothing before that, including the badminton years,
  is in `raw/`.

## Race history
- **18th October 2026:** Garmin Run 2026, 21KM. First half marathon.
  - 2:25:57 on the watch for 21.16 km. Start 04:02, 26 °C.
  - Slept 2–2.5 hours the night before. That night is missing from the wellness data.
  - Average HR 177; 182–189 from km 2 to km 8.
  - Cramp in the right calf at km 13, then the right hamstring, left calf, right quad and left
    quad. About 7 km of cramping and limping to the finish.
  - Splits: 6:03–6:54/km to km 15, except km 10 at 7:23. From km 16, 7:13–8:14/km, except km 20
    at 6:32. Cadence fell from about 176 to 152–164 spm.

## Upcoming events
- **22nd November 2026:** Galaxy Run 2026, 21KM (https://vm.vnexpress.net/galaxy-run-2-2026)
  - Registered. A redemption run for 18th October. A goal sub-2:10, set on 29th October. Pacing
    and fallbacks are in `PLAN.md`.
- **9th May 2027:** Ironman 70.3 Da Nang (https://www.ironman.com/races/im703-danang)
  - Goal sub-7:00, stretch sub-6:30. Swim in freestyle.

## Current block
- **A race:** Ironman 70.3 Da Nang
- **Phase:** Galaxy Run block to 29th November (W0–W4), then Base 1 from 30th November.
  Calendar and sessions in `PLAN.md`.
- **Weekly hours available:** 12+ (swim, bike, run, long run, long ride, brick, gym)
- **Weekly hours target:**
  - November build weeks (W1–W2): 10.5 h. Less in the taper and recovery weeks.
  - Base: 13.5–15 h.
  - Build: 13–15.5 h.
  - Specific: 12.5–15 h.
  - Recovery weeks: about 60–65 % of the week before.
  - The two lessons are about 3 h of each week, and the gym about 2.5 h in Base.
- **Gym is for:** strength, durability, mobility, functional work and physique (chest,
  shoulders, back, arms, abs, legs).
  - From 30th November: three sessions a week (Upper A, Legs, Upper B), at a gym with machines
    and free weights.
  - Before that: Upper A on Mondays only.

## Weekly schedule
Trains every day. Only the swim lessons are fixed; the rest can move to fit the training plan.
The week follows `PLAN.md`, which holds the sessions. This is its shape from 30th November.
The Galaxy Run block in November has its own days in `PLAN.md`.

| Day | Morning | Evening |
|---|---|---|
| Monday | rest | gym: Upper A |
| Tuesday | bike quality | gym: Legs |
| Wednesday | — | swim lesson (fixed) |
| Thursday | sleep in | run quality |
| Friday | easy ride | swim lesson (fixed) |
| Saturday | long run | own swim, then gym: Upper B |
| Sunday | long ride + brick run | nap |

- Badminton is paused until after 9th May 2027. It was on Monday, 19:00–21:00.
- Three early starts a week: Tuesday, Friday and Sunday. Never on the morning after a lesson
  night.

Time constraints:
- **Rides:** 04:00–06:30. Fewer vehicles, less dust and fewer people, so the ride is about
  riding, not about weaving through traffic.
- **Swim nights:** lessons end around 19:30 and the pool is far. Home at 20:30–21:00, and
  after dinner and a shower it is 22:30–23:00. An early night on Wednesday and Friday is hard.

## Thresholds and zones
Garmin is the source of truth. `raw/profile.json` holds the current HR zones per sport, power
zones, lactate threshold and FTP, refreshed on every sync. They are not copied here, because
copies go stale.

Not tested yet: bike FTP and swim CSS. Garmin's FTP left its 200 W placeholder on 25th October
2026, the day of the 150 km ride, but not from a test.

## Injury history and constraints
- No injuries so far (27th October 2026).
- Cramps in the 18th October half marathon (see Race history): the open issue before 22nd
  November.

## Equipments

### Tracking 
- Watch: Garmin Forerunner 265s. The Garmin record starts on 29th May 2026.
- Chest strap: Garmin HRM 600, since 24th June 2026; every run since then uses it. Heart rate
  before that is from the wrist.
- Bike computer: Garmin Edge 540, since 19th October 2026. Earlier rides were recorded on the
  watch as `cycling`; Edge rides are `road_biking`. The first Edge ride, 19th October, has no
  heart rate.

### Swim
- Goggles: Speedo Biofuse
- Swim trunk: Speedo Eco Endurance+

### Bike
- Bike: X-Lab RS5 size XS (https://xds.co/en-intl/products/rs5), bought 27th September 2026
- Tyres: GP5000S TR 700x32
- Pedals: Shimano PD-R550
- Power meter: built-in Branta Alloy Power Meter Crankset, on every ride since 27th September 2026
- Cycling shoes:
- Smart trainer:

### Run
- Shoes: ASICS Novablast 5 (26.0 cm, wide version)

> Note when equipment changes — it creates step changes in the data that  look like fitness changes but aren't.
