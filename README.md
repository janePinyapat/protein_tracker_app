# Protein & Recovery Tracker

A local web app for tracking daily protein intake to support exercise
recovery or PCOS-related nutrition goals.

Built with Python, Streamlit, SQLite, pandas, and Plotly — same structure
as the [Student Budget Tracker](../student-budget-tracker-option-2-mvp),
adapted for protein instead of money.

## Features

- Log food entries with protein grams, calories, meal type, and protein source
- Set separate daily protein targets for rest days and training days
- View today's protein total against the goal, with a progress bar
- View protein breakdown by source (meat, dairy, plant-based, etc.) and by meal
- View a daily protein trend chart against the goal line
- Filter and delete saved food entries
- Demo data included for portfolio use

## Project Structure

```text
protein-recovery-tracker/
├── app.py
├── pages/
│   ├── overview.py
│   ├── log_food.py
│   └── set_goal.py
├── database.py
├── analytics.py
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

## Database

SQLite file `protein_tracker.db`, created locally, ignored by Git.

Two tables:

- `food_log` — one row per food entry (description, protein_grams, calories,
  meal_type, protein_source, log_date)
- `protein_goals` — one row per day type (`Rest day` / `Training day`) with a
  `daily_target_grams` value

## Why Two Goal Types

Protein needs for muscle recovery are typically higher on training days than
rest days. Splitting the goal by day type (instead of one fixed number) keeps
the target realistic without needing a full macro-calculator.
