# Protein & Recovery Tracker

A local web app for tracking daily macros (protein, carbs, fat, fiber) to
support exercise recovery or PCOS-related nutrition goals — with your own
descriptive labels instead of the app judging what's "good" or "bad".

Built with Python, Streamlit, SQLite, pandas, and Plotly — same structure
as the [Student Budget Tracker](../student-budget-tracker-option-2-mvp),
adapted for nutrition instead of money.

## Features

- Log food entries with protein, carbs, fat, and fiber grams, plus calories,
  meal type, and protein source
- Optionally look up a food in the **Swedish Food Agency's food composition
  database** (Livsmedelsverket) and scale its macros to your portion,
  instead of typing them by hand
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
│   ├── overview.py      (Daily / Weekly dashboard)
│   ├── log_food.py       (log entries + USDA lookup)
│   └── set_goal.py       (protein & fiber targets)
├── database.py
├── analytics.py
├── usda_api.py           (FoodData Central client)
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

## USDA FoodData Central Lookup (Optional)

The Log Food page can search [USDA FoodData
Central](https://fdc.nal.usda.gov/) instead of you typing macros by hand.
Nutrition numbers come from that public database rather than being
hardcoded in this project.

Without any setup, lookups use the shared `DEMO_KEY`, which is heavily rate
limited (a handful of requests per hour) and fine only for a first look. To
raise that limit, get a free key at
[fdc.nal.usda.gov/api-key-signup.html](https://fdc.nal.usda.gov/api-key-signup.html)
and set it as an environment variable before running the app:

```powershell
$env:USDA_API_KEY = "your-key-here"
python -m streamlit run app.py
```

Or add it to `.streamlit/secrets.toml` (already gitignored) as
`usda_api_key = "your-key-here"`. No key is ever stored in this repository,
and the app works fully without one — you can always enter macros manually.

## Database

SQLite file `protein_tracker.db`, created locally, ignored by Git.

Three tables:

- `food_log` — one row per food entry (description, protein/carbs/fat/fiber
  grams, calories, meal_type, protein_source, log_date)
- `food_tags` — one row per (entry, label) pair, so a food can carry several
  of your own labels
- `protein_goals` — one row per day type (`Rest day` / `Training day`) with
  `daily_target_grams` and an optional `fiber_target_grams`

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
