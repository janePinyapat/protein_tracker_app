# Protein & Recovery Tracker

Built for women's nutrition, hydration, sleep, and recovery. A local web
app for tracking daily macros (protein, carbs, fat, fiber), water, and
sleep to support exercise recovery or PCOS-related nutrition goals — with
your own descriptive labels instead of the app judging what's "good" or
"bad". Wherever a source guideline differentiates by sex (fiber, water),
this app uses the figures published for adult women; see [Profile &
Suggested Targets](#profile--suggested-targets) for exact sources.

Built with Python, Streamlit, SQLite, pandas, and Plotly — same structure
as the [Student Budget Tracker](../student-budget-tracker-option-2-mvp),
adapted for nutrition instead of money.

## Features

- A short first-run profile (diet type, purpose, optional weight) that
  suggests protein and fiber targets and reorders which food labels are
  suggested first — editable anytime from the Profile page, first in the nav
- Log food entries with protein, carbs, fat, and fiber grams, plus calories,
  meal type, and protein source
- Optionally look up a food in the **Swedish Food Agency's food composition
  database** (Livsmedelsverket) and scale its macros to your portion,
  instead of typing them by hand
- Optionally take or upload a photo of your food and have Claude (Anthropic's
  AI) identify what's in it and estimate macros, which you review and edit
  before saving — a visual guess, not a lab measurement
- Apply your own descriptive labels to a food (e.g. "low glycemic", "high
  fiber", "home cooked") — the app only counts and charts the labels you
  choose, it never rates or ranks a food
- Set separate daily protein and fiber targets for rest days and training
  days, and get **breakfast/lunch/dinner recipe ideas from Spoonacular**
  each day, sized to whatever's left of today's target
- **Log Water**: one-tap quick-add buttons (+250 ml, +500 ml) or a custom
  amount in ml/fl oz, an optional daily target with a progress bar, and a
  saved-entries table you can filter and delete from
- **Log Sleep**: log hours slept for any date (re-logging the same date
  updates it instead of duplicating), optional notes, and an optional daily
  sleep target
- **Daily dashboard**: macro totals, calorie-by-macro split, protein by
  source, macros by meal, your labels for the day, and today's water/sleep
  against your targets
- **Weekly dashboard**: days logged, average macros per logged day, days
  meeting your protein goal, a full Monday–Sunday chart, your labels for
  the week, and average water/sleep per logged day with a weekly chart
- Filter and delete saved food entries by date, meal, source, or label
- Demo data included for portfolio use

## Project Structure

```text
protein-recovery-tracker/
├── app.py
├── pages/
│   ├── profile.py           (diet type, purpose, weight/height — first page)
│   ├── onboarding.py        (first-run version of the profile page)
│   ├── meal_recommendations.py (meal ideas + protein/fiber target form)
│   ├── log_food.py          (log entries + food-database lookup + AI photo)
│   ├── log_water.py         (quick-add water logging + target)
│   ├── log_sleep.py         (sleep logging + target)
│   └── overview.py          (Daily / Weekly dashboard)
├── database.py
├── analytics.py
├── wellness.py             (water/sleep conversion + weekly averaging)
├── user_profile.py        (profile vocabulary + tag/target personalization)
├── nutrition_targets.py   (protein/fiber target calculation + sources)
├── livsmedelsverket_api.py (Swedish Food Agency client)
├── food_photo_ai.py       (Claude vision food-photo client)
├── meal_recommendation_api.py (Spoonacular recipe-search client)
├── food_tags.py           (shared label vocabulary)
├── tests/
├── requirements.txt
└── README.md
```

## How To Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

To load demo data, run once in a Python shell (with the venv active):

```python
from database import seed_dummy_data
seed_dummy_data()
```

To run tests:

```powershell
python -m pytest tests
```

## Nutrition Lookup (Optional)

The Log Food page can search [Livsmedelsverkets
Livsmedelsdatabasen](https://dataportal.livsmedelsverket.se/livsmedel/swagger/index.html)
(the Swedish National Food Agency's food composition database) instead of
you typing macros by hand. Nutrition numbers come from that public database
rather than being hardcoded in this project.

No API key or sign-up is needed — the API is free and open. Food names and
dishes are returned in English but are mostly Swedish in origin (the
database covers ~2,600 foods commonly eaten in Sweden), so not every food
you search for will have a match. You can always skip the lookup and enter
macros manually.

There is no server-side search endpoint, so the app fetches the full food
list once (cached for a day) and matches your search text locally. Per
Livsmedelsverket's terms of reuse, the app credits the source in the UI:
"Livsmedelsverkets Livsmedelsdatabasen" (CC BY 4.0).

## Photo Logging (Optional, AI-Assisted)

The Log Food page can also take or accept a photo of your food and send it
to Claude (Anthropic's AI model) to identify what's shown and estimate its
macros. This is a genuinely different kind of source from the two lookups
above: it's a general-purpose vision model guessing from an image, not a
measured food-composition database, so treat the numbers as a rough starting
point — review and edit every field before saving, same as with any other
lookup.

This feature calls a paid external API and needs your own Anthropic API key:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
python -m streamlit run app.py
```

Or add it to `.streamlit/secrets.toml` (already gitignored) as
`anthropic_api_key = "sk-ant-your-key-here"`. Get a key at
[console.anthropic.com](https://console.anthropic.com/). Without a key
configured, this section shows a clear error and the rest of the app
(including manual entry and the Swedish Food Database lookup) works exactly
as before.

## Meal Recommendations

The **Meal Recommendations** page (second in the nav) searches
[Spoonacular's](https://spoonacular.com/food-api) recipe database for one
real breakfast, lunch, and dinner recipe each, sized to whatever protein and
fiber is still left of today's target once you subtract what you've already
logged. Each card shows the source recipe (with a link), a "ready in / serves"
caption, and estimated macros — and a "Log this meal" button jumps straight
to Log Food with that meal's macros and meal slot pre-filled, ready to
review and save.

No AI model is involved here — it's a direct nutrient-range search
(`complexSearch` filtered by recipe type and protein/fiber) against a real
recipe database. Needs its own free API key:

```powershell
$env:SPOONACULAR_API_KEY = "your-key-here"
python -m streamlit run app.py
```

Or add `spoonacular_api_key = "your-key-here"` to `.streamlit/secrets.toml`
(already gitignored). Get a free key at
[spoonacular.com/food-api](https://spoonacular.com/food-api/console#Dashboard)
— signup only, no payment required, ~150 free requests/day (this feature
uses about 3 per generation).

- **Respects your diet type from Profile** — Vegetarian, Vegan, and
  Pescatarian are passed straight to Spoonacular's own `diet` filter, so
  results are excluded by the recipe database itself rather than fetched
  and then discarded. Omnivore and "Other / prefer not to say" apply no
  filter. The page shows a caption naming the active filter when one applies.
- **Avoids repeating recent recommendations** — every recipe shown is
  logged with its Spoonacular id, and new searches page past anything
  recommended in the last 14 days (see `REPEAT_AVOIDANCE_DAYS` in
  `pages/meal_recommendations.py`) before falling back to a repeat only if
  a diet/meal-type combination's candidate pool is too small to avoid one —
  and says so in the UI when that happens, rather than silently repeating.
- **Today's remaining protein/fiber is split** 25% / 35% / 40% across
  breakfast / lunch / dinner — a simple fixed heuristic, not personalized
  meal-timing advice — then each meal is searched for within a window
  around its share.
- Spoonacular's recipe categories don't distinguish lunch from dinner (both
  map to "main course"), so those two rely on the search window and
  duplicate-avoidance to end up different, rather than a true category split.
- Recommendations are generated **once per calendar date** and cached (a
  `meal_recommendations` table, one row per date + meal type); revisiting
  the page the same day shows the cached ideas immediately, with no new API
  call. A "Refresh" button regenerates them on demand — useful after logging
  food shifts your remaining target.
- These are real recipes matched by diet and macro content, not a
  personalized meal plan or medical/dietary advice — check the source, and
  treat the listed macros as that recipe's own nutrition estimate.
- If no protein target is set yet for the selected day type, this section
  prompts you to set one first (in the "Set Daily Targets" section further
  down the same page) rather than guessing at what to recommend.

## Water & Sleep Logging

Two dedicated pages, following the same target philosophy as protein/fiber:
a suggested starting point where a sourced calculation exists, always
editable by hand.

**Log Water** — tap "+250 ml" or "+500 ml" to log instantly (no form), or
open "Log a custom amount or a different date" for any other amount in ml or
fl oz. Today's total is shown with a progress bar toward your water target.
Adding your weight on the Profile page suggests a starting water target (see
[Profile & Suggested Targets](#profile--suggested-targets)); you can
override it anytime in the "Set your water target" form on this page. Saved
entries can be filtered by date and deleted.

**Log Sleep** — pick a date (defaults to today) and enter hours slept, with
an optional note. Logging the same date again updates that entry rather than
creating a duplicate, since sleep is naturally one entry per night. There is
no comparable weight-based sleep guideline to calculate from, so the sleep
target is always fully user-set, same as before. Saved entries are listed
most-recent-first and can be deleted.

Both targets, plus today's/this week's water and sleep, appear on the
Dashboard alongside your macros.

## Profile & Suggested Targets

The Profile page (first in the nav, and shown once automatically on first
run as onboarding) asks for a diet type, one or more purposes ("PCOS
management", "Strength training / muscle recovery", "General health
tracking", "Other"), and optional weight and height.

- Diet type and purpose reorder which tags are suggested first when logging
  food — nothing is ever hidden; every starter tag stays available to
  everyone regardless of profile.
- If a weight is given, the app calculates suggested Rest day / Training day
  protein targets, a fiber target, and a daily water target, and saves them
  as your targets immediately. When more than one purpose is selected, the
  higher applicable protein rate is used (so, e.g., PCOS management plus
  strength training gets the strength-training level, not a diluted
  average).
- If both weight and height are given, the page also shows your BMI (World
  Health Organization formula and category) as general context. Height
  doesn't feed into the protein/fiber/water calculations — those are dosed
  from bodyweight per the cited guidelines, and BMI isn't a recognized input
  for any of them (there is no validated clinical formula linking water
  needs to BMI). A caption next to the BMI number notes its known
  limitation: it doesn't distinguish muscle from fat, so it reads
  misleadingly for very muscular or lean people, and that the WHO
  classification is the same for all adults — it isn't sex-specific.
- The "Your numbers" panel shows two rows: body stats (weight, height, BMI),
  then all four targets together (protein, fiber, water, sleep) — the water
  and sleep cards link straight to the Log Water / Log Sleep pages. The
  panel always reflects your current saved values, not just a one-time
  toast on save.

These are **starting points from published guidelines, not a personalized
medical recommendation** — see `nutrition_targets.py` for the exact sources
(Dietary Reference Intakes for the general protein RDA and the fiber
Adequate Intake for adult women; the International Society of Sports
Nutrition's position stand for the exercise range; the water target is body
weight scaled at 30 mL/kg/day — a commonly used clinical estimate — floored
at the beverage portion of the Dietary Reference Intake Adequate Intake for
adult women). Protein and fiber targets can be fine-tuned on the Meal
Recommendations page, water on the Log Water page, and the app says as much
in the UI. For targets tailored to your individual situation, talk to a
registered dietitian or your doctor.

## Database

SQLite file `protein_tracker.db`, created locally, ignored by Git.

Eight tables:

- `food_log` — one row per food entry (description, protein/carbs/fat/fiber
  grams, calories, meal_type, protein_source, log_date)
- `food_tags` — one row per (entry, label) pair, so a food can carry several
  of your own labels
- `protein_goals` — one row per day type (`Rest day` / `Training day`) with
  `daily_target_grams` and an optional `fiber_target_grams`
- `meal_recommendations` — one row per (date, meal type), the cached recipe
  ideas for a day, including each recipe's Spoonacular id (used to avoid
  recommending the same recipe again within the repeat-avoidance window)
- `user_profile` — a single row (diet type, purposes, optional weight) set
  on the Profile page
- `water_log` — one row per water entry (amount_ml, log_date)
- `sleep_log` — one row per date logged (`log_date` is unique; re-logging a
  date updates the existing row instead of adding a new one)
- `wellness_goals` — a single row (`water_target_ml`, `sleep_target_hours`)
  set from the Log Water / Log Sleep pages

`database.migrate_database()` adds the macro and fiber-target columns to a
database created by an earlier version of this app, without touching rows
already saved. It runs automatically on every page load.

## Why Two Goal Types

Protein needs for muscle recovery are typically higher on training days than
rest days. Splitting the goal by day type (instead of one fixed number) keeps
the target realistic without needing a full macro-calculator.

## On the Labels

Any tag you apply — "low glycemic", "high fiber", or one you type yourself —
is a label you chose, not a score the app assigns. Dashboards total and chart
labels back to you; they never rank one label as better than another or tell
you what to eat. For nutrition guidance specific to PCOS or recovery, talk to
a registered dietitian or your doctor.
