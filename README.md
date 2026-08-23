# Protein & Recovery Tracker

A local web app for tracking daily macros (protein, carbs, fat, fiber) to
support exercise recovery or PCOS-related nutrition goals — with your own
descriptive labels instead of the app judging what's "good" or "bad".

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
  days
- **Daily dashboard**: macro totals, calorie-by-macro split, protein by
  source, macros by meal, and your labels for the day
- **Weekly dashboard**: days logged, average macros per logged day, days
  meeting your protein goal, a full Monday–Sunday chart, and your labels for
  the week
- Filter and delete saved food entries by date, meal, source, or label
- Demo data included for portfolio use

## Project Structure

```text
protein-recovery-tracker/
├── app.py
├── pages/
│   ├── profile.py         (diet type, purpose, weight — first page)
│   ├── onboarding.py       (first-run version of the profile page)
│   ├── overview.py         (Daily / Weekly dashboard)
│   ├── log_food.py         (log entries + food-database lookup + AI photo)
│   └── set_goal.py         (protein & fiber targets)
├── database.py
├── analytics.py
├── user_profile.py        (profile vocabulary + tag/target personalization)
├── nutrition_targets.py   (protein/fiber target calculation + sources)
├── livsmedelsverket_api.py (Swedish Food Agency client)
├── food_photo_ai.py       (Claude vision food-photo client)
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

## Profile & Suggested Targets

The Profile page (first in the nav, and shown once automatically on first
run as onboarding) asks for a diet type, one or more purposes ("PCOS
management", "Strength training / muscle recovery", "General health
tracking", "Other"), and an optional weight.

- Diet type and purpose reorder which tags are suggested first when logging
  food — nothing is ever hidden; every starter tag stays available to
  everyone regardless of profile.
- If a weight is given, the app calculates suggested Rest day / Training day
  protein targets and a fiber target, and saves them as your daily targets
  immediately. When more than one purpose is selected, the higher applicable
  protein rate is used (so, e.g., PCOS management plus strength training
  gets the strength-training level, not a diluted average).

These are **starting points from published nutrition guidelines, not a
personalized medical recommendation** — see `nutrition_targets.py` for the
exact sources (Dietary Reference Intakes for the general RDA and fiber AI;
the International Society of Sports Nutrition's position stand for the
exercise range). You can fine-tune the resulting numbers anytime on the Set
Daily Targets page, and the app says as much in the UI. For targets tailored
to your individual situation, talk to a registered dietitian or your doctor.

## Database

SQLite file `protein_tracker.db`, created locally, ignored by Git.

Four tables:

- `food_log` — one row per food entry (description, protein/carbs/fat/fiber
  grams, calories, meal_type, protein_source, log_date)
- `food_tags` — one row per (entry, label) pair, so a food can carry several
  of your own labels
- `protein_goals` — one row per day type (`Rest day` / `Training day`) with
  `daily_target_grams` and an optional `fiber_target_grams`
- `user_profile` — a single row (diet type, purposes, optional weight) set
  on the Profile page

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
