# `training-data` — Implementation Plan v2

## Context

The repo is built through Part 8.4 of `docs/implementation-plan.md`: `fetch.py` works,
`decode.py` is pasted but not runnable, and `metrics.py` / `rollup.py` / `validate.py` are
empty files. The user's objection to v1 is that it assumes rather than verifies — it tells
you to go discover the API surface yourself (Part 6.6), leaves field paths marked
"PLACEHOLDER", and shapes `decode.py` around cycling.

So I did the verification v1 defers. I read the installed `garminconnect` 0.3.6 source,
diffed it against 0.3.15, pulled **all 47 August 2026 activities**, downloaded **one FIT per
distinct sport (9 of them)**, and fetched **all 31 days of August wellness**. Every claim in
v2 below is checked against that data.

The headline: the athlete does **no cycling at all**, badminton is their **largest single
load source**, and v1's core metrics — time-in-zone and aerobic decoupling — are **silently
broken on real data**, in ways that produce plausible-looking numbers rather than errors.

Scope note: the brief said "running, cycling, swimming and strength". The data says running,
**badminton**, strength, swimming, walking, hiking, breathwork — and zero cycling. v2 covers
what exists and leaves the cycling slot wired but dormant.

---

## What the data actually says

**August 2026 — 47 activities, 9 sports** (`get_activities_by_date`, one call):

| sport (`typeKey`) | sessions | load | hours |
|---|---:|---:|---:|
| `badminton` | 9 | **1411** | 18.6 |
| `running` | 11 | 1356 | 14.1 |
| `strength_training` | 9 | 85 | 2.3 |
| `treadmill_running` | 1 | 80 | 0.7 |
| `walking` | 9 | 59 | 3.9 |
| `lap_swimming` | 2 | 48 | 2.3 |
| `hiking` | 2 | 21 | 1.3 |
| `open_water_swimming` | 1 | 4 | 0.5 |
| `breathwork` | 2 | 0 | 0.2 |
| **total** | **47** | **3063** | **43.8** |

Walking is 9% of hours and 2% of load. Any hours-based weekly view misrepresents the month.

**FIT `sport` and Connect `typeKey` are different vocabularies** — verified per sport:

| Connect `typeKey` | FIT `sport` | FIT `sub_sport` |
|---|---|---|
| `running` | `running` | `generic` |
| `treadmill_running` | `running` | `treadmill` |
| `badminton` | **`racket`** | `badminton` |
| `strength_training` | **`training`** | `strength_training` |
| `breathwork` | `training` | `breathing` |
| `lap_swimming` | `swimming` | `lap_swimming` |
| `open_water_swimming` | `swimming` | `open_water` |
| `walking` / `hiking` | `walking` / `hiking` | `generic` |

**Records are not 1 Hz.** Measured median sample interval:

| sport | records | timer_s | median Δt | effective Hz |
|---|---:|---:|---:|---:|
| running, treadmill, swimming, breathwork | — | — | 1.0 s | 1.00 |
| `strength_training` | 1170 | 2233 | 1.0 s | 0.52 |
| `hiking`, `walking` | 902 / 677 | 3131 / 2318 | 3.0 s | 0.29 |
| **`badminton`** | 3037 | 11805 | **4.0 s** | **0.26** |

**Per-sport field availability** (why one `summarise()` shape cannot work):

- `lap_swimming` records carry **only `timestamp` + `heart_rate`**. Distance and pace live in
  `length_mesgs` / `lap_mesgs`.
- `strength_training` records carry only timestamp/distance/HR/temperature, but the file has
  **`set_mesgs` (51 sets)** with `category`, `repetitions`, `weight`, `set_type` and
  `exercise_title_mesgs` with readable names.
- `badminton` has HR + `enhanced_speed` + respiration; no power, no useful distance.
- `running` / `treadmill_running` have native **running power** (`power`, `normalized_power`)
  plus full running dynamics from the HRM 600.
- **No record stream anywhere has a `speed` or `altitude` field** — they are
  `enhanced_speed` and `enhanced_altitude`.

**Every FIT carries `time_in_zone_mesgs`** with the watch's own boundaries and totals, and
`training_load_peak` (== Connect's `activityTrainingLoad`). These are free, consistent, and
cross-sport. Two handling rules, both verified:

- Select the entry with **`reference_mesg == 'session'`**. Files carry one entry per lap as
  well — the Sept long run has 30 of them — and `[0]` is not guaranteed to be the session.
- `time_in_hr_zone` is **seven buckets**: `[below-Z1, Z1…Z5, above-Z5]`. Connect's
  `hrTimeInZone_1..5` is only the middle five, and the dropped below-Z1 bucket is not small:

| sport | timer | FIT 7-bucket sum | meta.json 5-field sum | below-Z1 share |
|---|---:|---:|---:|---:|
| `strength_training` | 2233 | 2212 | **2** | 100% |
| `open_water_swimming` | 1790 | 1790 | **0** | 100% |
| `breathwork` | 335 | 278 | **0** | 100% |
| `walking` | 2318 | 2318 | 425 | 82% |
| `hiking` | 3131 | 3131 | 582 | 81% |
| `lap_swimming` | 5786 | 5763 | 1540 | 73% |
| `badminton` | 11805 | 11805 | 7724 | 35% |
| `running` / `treadmill_running` | — | ≈timer | ≈timer | 1% |

Sourcing `garmin_z*_s` from `.meta.json` would report a strength session as **2 seconds** of
zone time. **Use the FIT's seven-element array**, with the same seven bucket definitions on
the `computed_*` side so the two namespaces are comparable.

---

## The five defects in v1, with measured impact

**1. `time_in_zones()` counts records as seconds.** Correct only at 1 Hz.

| sport | v1 zone total as % of actual timer |
|---|---:|
| `badminton` | **25.0%** — 8858 s of a 3h17m session vanish |
| `hiking` | 28.4% |
| `walking` | 28.9% |
| `strength_training` | 52.4% |

Weighting each record by its Δt (capped at 10 s to absorb pauses) brings every sport to
96–102% of timer. Verified against Garmin's own `time_in_hr_zone`, which totals to timer
almost exactly.

**2. `athlete.toml` zone bounds have dead gaps.** `z1=[0,142]`, `z2=[143,157]` with
`lo <= hr < hi` leaves 142, 157, 171, 186 and 201 in **no zone**. On the 2h19 long run this
discarded **1347 s (22 min, 16% of the run)**. The watch's actual boundaries are
`[126, 141, 156, 171, 186, 201]` on `percent_hrr` — contiguous, and different from
`athlete.toml`'s, so the two sets could never reconcile. **Decision taken: adopt the watch's
zones as canonical.**

**3. `aerobic_decoupling()` returns `None` on every activity, always.**
`summarise()` passes `output_key = "power" if sport == "cycling" else "speed"`. `sport` is
`"running"`, never `"cycling"`, so every activity uses `"speed"` — a field that does not
exist in any record stream. The filter matches zero records and the function returns `None`
before it can compute anything. A flagship metric that has never once produced a number.

**4. Sport keys never match, so every activity is scored against run zones.**
`athlete["zones"].get(sport)` is looked up with FIT's `"running"`/`"racket"`/`"training"`
against `athlete.toml` keys `run`/`cycling`. **Every lookup misses**, and the
`athlete["zones"]["run"]` fallback makes runs look correct while badminton, swimming and
strength are silently scored on run zones.

**5. CTL/ATL runs on weekly rows with per-day decay constants.** `training_load_series` is
fed one row per ISO week but keeps `ctl_days=42`, `atl_days=7`. On August's real loads:

```
daily, zero-filled (correct) : ctl=51.2  atl=89.6  tsb=-51.7
weekly rows (v1 as written)  : ctl=68.3  atl=294.6 tsb=-273.3
```

A TSB of −273 is not a number that means anything. The `total_h * 50` proxy is separately
wrong: it produces weekly loads `[209, 671, 377, 419, 483, 31]` against Garmin's actual
`[382, 814, 251, 800, 814, 3]` — week 4 is understated by half, because 3.9 h of walking and
18.6 h of badminton are priced identically.

**Also wrong, lower impact:**

- `downsample()` buckets by list index, so `t_min` is a 4× compressed axis on badminton.
  It also reads `speed`/`altitude`/`power`, giving **three permanently empty columns** for
  most sports.
- `rollup.build_wellness()` reads `training_status["trainingStatus"]` → `KeyError`. Real path
  is `training_status.mostRecentTrainingStatus.latestTrainingStatusData.<deviceId>.trainingStatus`,
  **keyed by device id** (so it cannot be hardcoded) and an **integer code**, not a string.
- `normalized_power()` recomputes from records when the FIT already carries
  `session.normalized_power` (221 vs the recomputed value) and Connect carries `normPower`.
- Part 9 claims lat/lon "stays in the FIT archive". The committed `*.meta.json` carries
  `startLatitude`, `startLongitude`, `ownerFullName`, `ownerId` and profile image URLs in
  plaintext.

---

## Verified reference data (replaces v1 Part 6.6)

`docs/api-notes.md` gets written from this, not from a discovery exercise.

**Library.** 0.3.6 was installed when this was written; step 1 moves the pin to 0.3.15.
Static diff: **no methods removed, every method this pipeline uses has an unchanged
signature**; only `get_activities` and `set_blood_pressure` changed (both unused).
**Decision taken: bump to 0.3.15** for the 0.3.10/0.3.11 token-storage hardening and these
new bulk endpoints:

| method | replaces | saving |
|---|---|---|
| `get_rhr_daily(s, e)` | 1 call/day | ~1 year per call |
| `get_hrv_data_range(s, e)` | 1 call/day | whole range per call |
| `get_sleep_daily(s, e)` | 1 call/day | auto-chunks at 28 d |
| `get_max_metrics_range(s, e)` | 1 call/day | whole range per call |
| `get_heart_rate_zones()` | — | the watch's configured zones |

**Wellness field paths, null-rates measured over all 31 August days:**

| path | present | sample |
|---|---:|---|
| `stats.restingHeartRate` | 31/31 | 52 |
| `stats.averageStressLevel` / `.totalSteps` / `.bodyBatteryHighestValue` | 31/31 | 33 / 12694 / 87 |
| `sleep.dailySleepDTO.sleepTimeSeconds` | 28/31 | 26880 |
| `sleep.dailySleepDTO.sleepScores.overall.value` | 28/31 | 78 |
| `hrv.hrvSummary.lastNightAvg` | 28/31 | 49 |
| `hrv.hrvSummary.status` / `.weeklyAvg` | 30/31 | `BALANCED` / 47 |
| `training_readiness[wakeup].score` / `.acuteLoad` / `.recoveryTime` | 31/31 | 64 / 606 / 1048 |
| `…latestTrainingStatusData.<dev>.trainingStatus` | 31/31 | `2` (= `UNPRODUCTIVE_3`) |
| `training_status.mostRecentVO2Max.generic.vo2MaxPreciseValue` | 31/31 | 46.2 |
| `…metricsTrainingLoadBalanceDTOMap.<dev>.monthlyLoadAerobicLow` | 31/31 | 1814.3 |
| `…latestTrainingStatusData.<dev>.weeklyTrainingLoad` | **0/31** | **always null — do not use** |

**`training_readiness` snapshot selection is not cosmetic.** Garmin returns 2–8 snapshots per
day (August: 2 on 6 days, up to 8 on one). The list is **newest-first**, so the library's
`get_morning_training_readiness()` `next()` picks the *latest* `AFTER_WAKEUP_RESET`. On
2026-09-01 that is the 13:05 reading (score 35) rather than the 04:30 one (score **51**) — a
16-point swing. **Select `min(timestampLocal)` among `AFTER_WAKEUP_RESET`.**

**Endpoints that return empty for this account/device** (FR265s) — do not build on them:
`get_running_tolerance(...)` → `[]`, `get_endurance_score(...)` → `{}`.

**Endpoints v1 never mentions that matter for the 18 Oct half marathon:**

- `get_race_predictions()` → `timeHalfMarathon: 7897` (2:11:37), plus 5K 25:37, 10K 56:38.
- `get_lactate_threshold(latest=True)` → `heartRate: 192`, and running
  `functionalThresholdPower: 264` at `weight: 62.0`.

**`athlete.toml` is stale against all of this:** `run_lthr = 0` (actual **192**, confirmed by
two independent sources — the endpoint and FIT `threshold_heart_rate`); `weight_kg = 60.0`
(Garmin has **62.0**, set 2026-09-07); `resting_hr_baseline = 53` (observed 49–52). The `264`
is **running** power threshold — it must not be written into `bike_ftp`.

---

## Revised design

**Canonical sport key = Connect `activityType.typeKey`.** It is flat and already separates
`treadmill_running` from `running`. `decode.py` derives it from FIT `(sport, sub_sport)` via
an explicit map and asserts agreement with the sibling `.meta.json`, so a new sport fails
loudly instead of silently falling back.

**A sport registry, not an if-chain.** One entry per `typeKey` declaring capability flags —
`has_power`, `has_pace`, `has_distance`, `has_sets`, `has_lengths`, `counts_as_training` —
plus a default handler so an unseen sport degrades to HR-and-duration rather than crashing.
Registry entries are seeded from the nine sports verified above; `cycling` is defined but
dormant until data exists.

**Two namespaces, never mixed.** `garmin_*` columns come from Garmin
(`activityTrainingLoad`, the FIT's seven-bucket `time_in_hr_zone`, `normPower`, TE).
`computed_*` columns are ours, over the same seven buckets. They are allowed to disagree;
that disagreement is diagnostic — but only if both sides count the same thing.

**Load currency is `activityTrainingLoad`**, not hours and not a proxy. It is present for
every sport and is the only number that prices badminton against running correctly.

### Module changes

| file | change |
|---|---|
| `config.py` | add `SPORTS` registry; drop `zones` from athlete config reads |
| `garmin.py` | unchanged except the 0.3.15 bump |
| `fetch.py` | range endpoints for rhr/hrv/sleep/max-metrics; strip PII from `.meta.json` before write; widen `ACTIVITY_LOOKBACK_DAYS` |
| `decode.py` | **rewrite**: per-sport summarise, Δt-weighted zones, elapsed-time stream buckets, `enhanced_*` fields, `set_mesgs`/`length_mesgs` |
| `metrics.py` | **write**: `time_in_zones_weighted`, `decoupling`, daily `training_load_series`, zone-boundary parsing |
| `rollup.py` | **write**: correct wellness paths, daily CTL/ATL sampled to weekly, `garmin_*`/`computed_*` split |
| `validate.py` | **write**: thresholds from the measured null-rates above |

---

## Implementation order

Each step ends runnable. Do not start one until the previous is clean.

**1 — Bump the library.** `uv add "garminconnect==0.3.15"`. The diff should touch
`pyproject.toml`, the README's pin line, and only the `garminconnect` block of `uv.lock` —
the new floors (`curl_cffi>=0.15.0`, `requests>=2.33.0`) are already met by the lock.

- **Back up the token inside `~/.garminconnect/`, never beside it.** A sibling
  `~/.garminconnect.bak/` is *not* matched by the dotfiles `.garminconnect/` ignore rule, so it
  would put the MFA-bypassing token where `dotfiles add -A` commits it. Use
  `cp -p ~/.garminconnect/garmin_tokens.json ~/.garminconnect/garmin_tokens.json.bak-0.3.6`,
  confirm with `check-ignore -v`, and delete the copy once the bump is verified.
- **Verify with a smoke test, not `fetch.py`.** `fetch.py` skips downloads for IDs already in
  `.sync-state.json`, so it never re-exercises `download_activity` on known activities, and
  with a 30-day lookback it drags weeks of new data into the same diff. The smoke test logs in
  through `training_data.garmin.client()`, lists Sept 1–2, re-downloads both known FITs and
  asserts they are byte-identical to `raw/`, and checks that all seven wellness responses keep
  the types captured under 0.3.6. Run it in a throwaway env
  (`uv run --no-project --with garminconnect==0.3.15`) before touching the pin, then again in
  the locked project env after `uv add`.
- **The MFA re-login risk is close to nil.** Both versions write and read the same three token
  keys (`di_token`, `di_refresh_token`, `di_client_id`), the new symlink check passes because
  nothing in the token path is a symlink, and only `logout()` ever deletes the token file.
  What remains is server-side: if Garmin rotates the refresh token, recover with
  `uv run python bin/login.py`, whose `Garmin(...)` constructor is unchanged.

**2 — `docs/api-notes.md`.** Transcribe the verified-reference section above. This is the file
v1 asked you to produce by hand; it now exists as fact.

**3 — Correct `athlete.toml` and `ATHLETE.md`.** Set `run_lthr = 192`, `weight_kg = 62.0`,
`resting_hr_baseline = 50`. **Delete the `[zones]` tables entirely** — zones now come from the
watch. Leave `bike_ftp`/`swim_css` at 0 and add a comment that `264` is running power, not
bike FTP. Add a `[sports]` section marking which `typeKey`s count as training.

**4 — Backfill August onto disk, before touching decode.** `raw/` currently holds two
September runs — one sport. Steps 5–8 cannot be exercised against nine sports until August's
47 FITs are local, and "don't start a step until the previous is clean" is unenforceable
without them. Widen `ACTIVITY_LOOKBACK_DAYS` to ~60 (or run a dated one-off) and re-run
`fetch.py`. ~47 downloads at 1.5 s plus wellness; expect a few minutes.

**5 — `metrics.py`.** Pure functions, no I/O:
- `zone_bounds_from_fit(messages)` → boundaries from the `reference_mesg == 'session'` entry's
  `hr_zone_high_boundary`, expanded to all seven buckets.
- `time_in_zones_weighted(records, bounds, cap_s=10)` → Δt-weighted seconds. **Assert the
  total lands within 5% of `total_timer_time`** — that assertion is what would have caught
  the badminton 25%.
- `decoupling(records, output_key)` → takes an explicit key from the registry
  (`power` for runs, `enhanced_speed` for hiking/walking, `None` → skip). Filter with
  **`is not None`, not truthiness** — v1's `if r.get(k)` drops every `0.0`, so stopped-time
  records vanish; if the two halves hold unequal stopped time that biases EF between them,
  which is exactly the quantity decoupling measures. Decide stopped-time handling explicitly
  (recommendation: drop records where the sport's output key is 0 *and* the athlete is
  paused, keep genuine zeros otherwise).
- `training_load_series(daily_load, ctl_days=42, atl_days=7)` → **daily**, zero-filled.

Sanity check, per v1 Part 10.1: 30 days of constant 100 → ATL ≈ 99, CTL ≈ 51.5, TSB ≈ −48.6.

**6 — `decode.py` rewrite.** Per-sport summarise driven by the registry; streams bucketed by
**elapsed seconds from `start_time`**, not list index; `enhanced_speed`/`enhanced_altitude`;
`normalized_power` read from the session, not recomputed; `set_mesgs` → a `sets` array for
strength (use `exercise_title_mesgs[].wkt_step_name[0]` only — later elements are decoder
artifacts); `length_mesgs` → per-length pace for pool swims; lat/lon excluded as v1 intended.
Capture `workout_rpe` and `workout_feel` from the session — the athlete already logs them.

**7 — `fetch.py` updates.** Swap in the range endpoints; strip `startLatitude`,
`startLongitude`, `endLatitude`, `endLongitude`, `owner*` from `.meta.json` before writing.
Note this changes already-committed files, so re-run over `raw/` once and commit the scrub.

**8 — `rollup.py`.** Four tables:
- `wellness-YYYY.csv` — verified paths; device-map iteration preferring `primaryTrainingDevice`;
  earliest-`AFTER_WAKEUP_RESET` readiness; VO2max, sleep score, load balance.
- `activities-YYYY.csv` — `garmin_*` and `computed_*` side by side.
- `weekly-YYYY.csv` — hours and load **per sport**, zone distribution, CTL/ATL/TSB sampled
  from the daily series, and a `training_h` column that excludes non-training sports.
- `race-YYYY.csv` — race predictions over time against the 18 Oct target. **Verify first:**
  only the no-arg `get_race_predictions()` form is confirmed working (one snapshot,
  `calendarDate: 2026-09-12`). A table over time needs the
  `_type='daily'` + `startdate`/`enddate` form, which I did not call — and two sibling range
  endpoints (`get_running_tolerance`, `get_endurance_score`) returned empty on this device.
  If the daily form comes back empty, drop this table rather than shipping a fourth empty
  column; the single latest prediction still belongs in `wellness-YYYY.csv`.

**9 — `validate.py`.** Data-driven thresholds: `rhr`/`steps`/`readiness` ≥ 95% of days,
`sleep_h`/`hrv` ≥ 85% (3/31 genuinely missing in August). Assert per-activity zone totals are
within 5% of timer, that no `computed_*` column is wholly null, and that every `typeKey` seen
has a registry entry.

**10 — Parts 13–17 of v1 carry over unchanged** — `bin/sync.sh`, the launchd agent, dotfiles
aliases, Claude wiring, backfill. The only edit: backfill gets much cheaper now that wellness
uses range endpoints, so the "several hours overnight" guidance can be relaxed for wellness
while staying conservative for FIT downloads.

---

## Verification

```bash
# 1. library bump is non-breaking — smoke test from step 1 (a throwaway script, not a repo
#    file): login, list Sept 1–2, byte-identical FIT re-download, wellness response types
cp -p ~/.garminconnect/garmin_tokens.json ~/.garminconnect/garmin_tokens.json.bak-0.3.6
uv add "garminconnect==0.3.15" && uv lock --locked
rm ~/.garminconnect/garmin_tokens.json.bak-0.3.6      # once the smoke test passes

# 2. metrics math (must match the numbers in step 5)
uv run python -c "
from training_data.metrics import training_load_series
print(training_load_series([100]*30)[-1])"

# 3. decode every sport (step 4 put August's 47 FITs on disk)
uv run python -m training_data.decode
uv run python -c "
import json, glob, collections
c=collections.Counter()
for p in glob.glob('activities/**/*.json', recursive=True):
    a=json.load(open(p)); c[a['sport']]+=1
print(c)"        # expect 9 distinct sports once August is fetched

# 4. the regression that matters — zone totals vs timer
uv run python -m training_data.validate   # fails if any activity is off by >5%

# 5. end to end
./bin/sync.sh
```

The August data behind the numbers in this document was a throwaway capture outside the repo
and no longer exists. Step 4 re-fetches August into `raw/`; from then on any claim here can be
re-checked against committed data.

---

## Open items, flagged not hidden

- `get_lactate_threshold().speed_and_heart_rate.speed = 0.3139` — units are ambiguous.
  `1/0.3139` gives 3.19 m/s (5:14/km), which sits oddly against a 2:11 HM prediction
  (~6:14/km). The HR (192) and power (264) from the same payload both cross-validate against
  the FIT, so only `speed` is in doubt. **Leave `run_threshold_pace_s_per_km` at 0 until a
  field test settles it** rather than writing a number we cannot defend.
- Garmin reported `trainingStatus = UNPRODUCTIVE_3` on **all 31 days of August**. Worth a
  look independently of this pipeline.
- `weeklyTrainingLoad` is null every day on this device; `monthlyLoadAerobic*` is populated
  and is the usable substitute.
