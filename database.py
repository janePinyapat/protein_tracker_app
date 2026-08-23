import sqlite3

import pandas as pd


DATABASE_NAME = "protein_tracker.db"

# Macro columns added after the protein-only MVP. Existing rows keep their
# protein value and get NULL macros until the user edits or re-logs them.
MACRO_COLUMNS = ["carbs_grams", "fat_grams", "fiber_grams"]


def create_connection():
    """Create a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_food_log_table():
    """Create the food log table if it does not already exist."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            protein_grams REAL NOT NULL,
            calories REAL,
            carbs_grams REAL,
            fat_grams REAL,
            fiber_grams REAL,
            meal_type TEXT NOT NULL,
            protein_source TEXT NOT NULL,
            log_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def create_protein_goals_table():
    """Create the protein goals table if it does not already exist."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS protein_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_type TEXT NOT NULL UNIQUE,
            daily_target_grams REAL NOT NULL,
            fiber_target_grams REAL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def create_food_tags_table():
    """Create the food tag table if it does not already exist.

    Tags are free text chosen by the user, stored one row per tag so a single
    food entry can carry several labels.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS food_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            UNIQUE (entry_id, tag),
            FOREIGN KEY (entry_id) REFERENCES food_log (id) ON DELETE CASCADE
        )
        """
    )

    connection.commit()
    connection.close()


def create_user_profile_table():
    """Create the single-row user profile table if it does not already exist.

    This app is single-user and local, so the profile is one row pinned to
    id=1 rather than keyed by a user id.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            diet_type TEXT NOT NULL,
            purposes TEXT NOT NULL,
            weight_value REAL,
            weight_unit TEXT,
            height_value REAL,
            height_unit TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def create_meal_recommendations_table():
    """Create the meal recommendations cache table if it does not exist.

    One row per (date, meal type) — regenerating a date's recommendations
    replaces its rows rather than appending to them.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rec_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            recipe_id INTEGER,
            meal_name TEXT NOT NULL,
            description TEXT,
            protein_grams REAL,
            fiber_grams REAL,
            calories REAL,
            source_title TEXT,
            source_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (rec_date, meal_type)
        )
        """
    )

    connection.commit()
    connection.close()


def create_water_log_table():
    """Create the water log table if it does not already exist.

    Multiple entries per day, same shape as ``food_log`` — log each glass as
    you drink it and the day's total is the sum.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS water_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount_ml REAL NOT NULL,
            log_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def create_sleep_log_table():
    """Create the sleep log table if it does not already exist.

    One row per date (sleep is naturally nightly) — logging the same date
    again updates that row rather than adding a second one.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sleep_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL UNIQUE,
            hours_slept REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def create_wellness_goals_table():
    """Create the single-row water/sleep target table if it does not exist.

    Same single-pinned-row shape as ``user_profile`` — one row for both
    targets, no day-type split.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS wellness_goals (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            water_target_ml REAL,
            sleep_target_hours REAL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def get_existing_columns(cursor, table_name):
    """Return the column names currently present on a table."""
    return [row[1] for row in cursor.execute(f"PRAGMA table_info({table_name})")]


def migrate_database():
    """Add columns introduced after the first release, keeping saved rows.

    SQLite has no ``ADD COLUMN IF NOT EXISTS``, so each column is checked
    against ``PRAGMA table_info`` before it is added. Running this repeatedly
    is safe.
    """
    connection = create_connection()
    cursor = connection.cursor()

    food_log_columns = get_existing_columns(cursor, "food_log")
    for column_name in MACRO_COLUMNS:
        if column_name not in food_log_columns:
            cursor.execute(f"ALTER TABLE food_log ADD COLUMN {column_name} REAL")

    goal_columns = get_existing_columns(cursor, "protein_goals")
    if "fiber_target_grams" not in goal_columns:
        cursor.execute(
            "ALTER TABLE protein_goals ADD COLUMN fiber_target_grams REAL"
        )

    profile_columns = get_existing_columns(cursor, "user_profile")
    if "weight_value" not in profile_columns:
        cursor.execute("ALTER TABLE user_profile ADD COLUMN weight_value REAL")
    if "weight_unit" not in profile_columns:
        cursor.execute("ALTER TABLE user_profile ADD COLUMN weight_unit TEXT")
    if "height_value" not in profile_columns:
        cursor.execute("ALTER TABLE user_profile ADD COLUMN height_value REAL")
    if "height_unit" not in profile_columns:
        cursor.execute("ALTER TABLE user_profile ADD COLUMN height_unit TEXT")

    meal_recommendation_columns = get_existing_columns(cursor, "meal_recommendations")
    if "recipe_id" not in meal_recommendation_columns:
        cursor.execute(
            "ALTER TABLE meal_recommendations ADD COLUMN recipe_id INTEGER"
        )

    connection.commit()
    connection.close()


def initialize_database():
    """Create every table and apply pending migrations."""
    create_food_log_table()
    create_protein_goals_table()
    create_food_tags_table()
    create_user_profile_table()
    create_meal_recommendations_table()
    create_water_log_table()
    create_sleep_log_table()
    create_wellness_goals_table()
    migrate_database()


def save_user_profile(
    diet_type,
    purposes,
    weight_value=None,
    weight_unit=None,
    height_value=None,
    height_unit=None,
):
    """Save or update the single user profile row."""
    connection = create_connection()
    cursor = connection.cursor()

    purposes_text = ", ".join(purposes) if purposes else ""

    cursor.execute(
        """
        INSERT INTO user_profile (
            id, diet_type, purposes, weight_value, weight_unit,
            height_value, height_unit
        )
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id)
        DO UPDATE SET
            diet_type = excluded.diet_type,
            purposes = excluded.purposes,
            weight_value = excluded.weight_value,
            weight_unit = excluded.weight_unit,
            height_value = excluded.height_value,
            height_unit = excluded.height_unit,
            updated_at = CURRENT_TIMESTAMP
        """,
        (diet_type, purposes_text, weight_value, weight_unit, height_value, height_unit),
    )

    connection.commit()
    connection.close()


def get_user_profile():
    """Read the user profile, or None if onboarding hasn't been completed."""
    connection = create_connection()

    row = connection.execute(
        """
        SELECT diet_type, purposes, weight_value, weight_unit,
               height_value, height_unit, updated_at
        FROM user_profile WHERE id = 1
        """
    ).fetchone()

    connection.close()

    if row is None:
        return None

    (
        diet_type,
        purposes_text,
        weight_value,
        weight_unit,
        height_value,
        height_unit,
        updated_at,
    ) = row
    purposes = (
        [purpose.strip() for purpose in purposes_text.split(",") if purpose.strip()]
        if purposes_text
        else []
    )

    return {
        "diet_type": diet_type,
        "purposes": purposes,
        "weight_value": weight_value,
        "weight_unit": weight_unit,
        "height_value": height_value,
        "height_unit": height_unit,
        "updated_at": updated_at,
    }


def save_meal_recommendations(rec_date, meals):
    """Replace the cached meal recommendations for one date with new ones.

    ``meals`` is a list of dicts with keys: meal_type, recipe_id, meal_name,
    description, protein_grams, fiber_grams, calories, source_title,
    source_url.
    """
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM meal_recommendations WHERE rec_date = ?", (rec_date,))

    for meal in meals:
        cursor.execute(
            """
            INSERT INTO meal_recommendations (
                rec_date, meal_type, recipe_id, meal_name, description,
                protein_grams, fiber_grams, calories, source_title, source_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec_date,
                meal["meal_type"],
                meal.get("recipe_id"),
                meal["meal_name"],
                meal.get("description"),
                meal.get("protein_grams"),
                meal.get("fiber_grams"),
                meal.get("calories"),
                meal.get("source_title"),
                meal.get("source_url"),
            ),
        )

    connection.commit()
    connection.close()


MEAL_TYPE_ORDER = "CASE meal_type WHEN 'Breakfast' THEN 1 WHEN 'Lunch' THEN 2 WHEN 'Dinner' THEN 3 ELSE 4 END"


def get_meal_recommendations(rec_date):
    """Read cached meal recommendations for one date, in meal order."""
    connection = create_connection()

    recommendations = pd.read_sql_query(
        f"""
        SELECT meal_type, recipe_id, meal_name, description, protein_grams,
               fiber_grams, calories, source_title, source_url, created_at
        FROM meal_recommendations
        WHERE rec_date = ?
        ORDER BY {MEAL_TYPE_ORDER}
        """,
        connection,
        params=(rec_date,),
    )

    connection.close()
    return recommendations


def get_recent_recommended_recipe_ids(since_date):
    """Distinct recipe ids recommended on or after ``since_date``.

    Used to steer new recommendations away from recent repeats. Only rows
    with a saved recipe_id count (older cached rows from before this column
    existed are silently skipped, not treated as a repeat).
    """
    connection = create_connection()

    rows = connection.execute(
        """
        SELECT DISTINCT recipe_id FROM meal_recommendations
        WHERE rec_date >= ? AND recipe_id IS NOT NULL
        """,
        (since_date,),
    ).fetchall()

    connection.close()
    return [row[0] for row in rows]


def add_water_entry(amount_ml, log_date):
    """Save one water log entry."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO water_log (amount_ml, log_date) VALUES (?, ?)",
        (amount_ml, log_date),
    )

    connection.commit()
    connection.close()

    return cursor.lastrowid


def get_all_water_entries():
    """Read all saved water entries, most recent first."""
    connection = create_connection()

    water_entries = pd.read_sql_query(
        """
        SELECT id, amount_ml, log_date, created_at
        FROM water_log
        ORDER BY log_date DESC, id DESC
        """,
        connection,
    )

    connection.close()
    return water_entries


def delete_water_entry(entry_id):
    """Delete one water entry by its id."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM water_log WHERE id = ?", (entry_id,))

    deleted_rows = cursor.rowcount
    connection.commit()
    connection.close()

    return deleted_rows


def save_sleep_entry(log_date, hours_slept, notes=None):
    """Save or update the sleep entry for one date."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sleep_log (log_date, hours_slept, notes)
        VALUES (?, ?, ?)
        ON CONFLICT(log_date)
        DO UPDATE SET
            hours_slept = excluded.hours_slept,
            notes = excluded.notes,
            created_at = CURRENT_TIMESTAMP
        """,
        (log_date, hours_slept, notes),
    )

    connection.commit()
    connection.close()


def get_all_sleep_entries():
    """Read all saved sleep entries, most recent night first."""
    connection = create_connection()

    sleep_entries = pd.read_sql_query(
        """
        SELECT id, log_date, hours_slept, notes, created_at
        FROM sleep_log
        ORDER BY log_date DESC
        """,
        connection,
    )

    connection.close()
    return sleep_entries


def get_sleep_entry(log_date):
    """Read the sleep entry for one date, or None if nothing was logged."""
    connection = create_connection()

    row = connection.execute(
        "SELECT hours_slept, notes FROM sleep_log WHERE log_date = ?",
        (log_date,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    hours_slept, notes = row
    return {"hours_slept": hours_slept, "notes": notes}


def delete_sleep_entry(log_date):
    """Delete the sleep entry for one date."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM sleep_log WHERE log_date = ?", (log_date,))

    deleted_rows = cursor.rowcount
    connection.commit()
    connection.close()

    return deleted_rows


def save_wellness_goals(water_target_ml=None, sleep_target_hours=None):
    """Save or update the single water/sleep target row."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO wellness_goals (id, water_target_ml, sleep_target_hours)
        VALUES (1, ?, ?)
        ON CONFLICT(id)
        DO UPDATE SET
            water_target_ml = excluded.water_target_ml,
            sleep_target_hours = excluded.sleep_target_hours,
            updated_at = CURRENT_TIMESTAMP
        """,
        (water_target_ml, sleep_target_hours),
    )

    connection.commit()
    connection.close()


def get_wellness_goals():
    """Read the water/sleep targets, or None if neither has been set."""
    connection = create_connection()

    row = connection.execute(
        "SELECT water_target_ml, sleep_target_hours, updated_at FROM wellness_goals WHERE id = 1"
    ).fetchone()

    connection.close()

    if row is None:
        return None

    water_target_ml, sleep_target_hours, updated_at = row
    return {
        "water_target_ml": water_target_ml,
        "sleep_target_hours": sleep_target_hours,
        "updated_at": updated_at,
    }


def add_food_entry(
    description,
    protein_grams,
    meal_type,
    protein_source,
    log_date,
    calories=None,
    carbs_grams=None,
    fat_grams=None,
    fiber_grams=None,
    tags=None,
):
    """Save one food log entry along with the tags the user applied."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO food_log (
            description, protein_grams, calories, carbs_grams, fat_grams,
            fiber_grams, meal_type, protein_source, log_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            description,
            protein_grams,
            calories,
            carbs_grams,
            fat_grams,
            fiber_grams,
            meal_type,
            protein_source,
            log_date,
        ),
    )

    entry_id = cursor.lastrowid

    for tag in clean_tags(tags):
        cursor.execute(
            "INSERT OR IGNORE INTO food_tags (entry_id, tag) VALUES (?, ?)",
            (entry_id, tag),
        )

    connection.commit()
    connection.close()

    return entry_id


def clean_tags(tags):
    """Normalise a list of user-entered tags.

    Blank entries are dropped, surrounding whitespace is trimmed, commas are
    replaced (tags are joined with commas when read back), and duplicates are
    removed while keeping the order the user chose.
    """
    if not tags:
        return []

    cleaned = []
    for tag in tags:
        if tag is None:
            continue
        normalised = str(tag).replace(",", " ").strip()
        if normalised and normalised not in cleaned:
            cleaned.append(normalised)

    return cleaned


FOOD_ENTRY_QUERY = """
    SELECT
        food_log.id,
        food_log.description,
        food_log.protein_grams,
        food_log.carbs_grams,
        food_log.fat_grams,
        food_log.fiber_grams,
        food_log.calories,
        food_log.meal_type,
        food_log.protein_source,
        food_log.log_date,
        food_log.created_at,
        COALESCE(GROUP_CONCAT(food_tags.tag, ', '), '') AS tags
    FROM food_log
    LEFT JOIN food_tags ON food_tags.entry_id = food_log.id
"""


def get_all_food_entries():
    """Read all saved food entries, with their tags joined into one column."""
    connection = create_connection()

    food_entries = pd.read_sql_query(
        FOOD_ENTRY_QUERY
        + """
        GROUP BY food_log.id
        ORDER BY food_log.log_date DESC, food_log.id DESC
        """,
        connection,
    )

    connection.close()
    return food_entries


def get_filtered_food_entries(
    log_date=None, meal_type=None, protein_source=None, tag=None
):
    """Read food entries filtered by date, meal type, source, and tag."""
    connection = create_connection()

    query = FOOD_ENTRY_QUERY
    parameters = []

    if tag and tag != ALL_TAGS:
        query += """
            WHERE food_log.id IN (
                SELECT entry_id FROM food_tags WHERE tag = ?
            )
        """
        parameters.append(tag)

    query += " GROUP BY food_log.id HAVING 1 = 1"

    if log_date:
        query += " AND food_log.log_date = ?"
        parameters.append(str(log_date))

    if meal_type and meal_type != ALL_MEALS:
        query += " AND food_log.meal_type = ?"
        parameters.append(meal_type)

    if protein_source and protein_source != ALL_SOURCES:
        query += " AND food_log.protein_source = ?"
        parameters.append(protein_source)

    query += " ORDER BY food_log.log_date DESC, food_log.id DESC"

    food_entries = pd.read_sql_query(query, connection, params=parameters)

    connection.close()
    return food_entries


ALL_MEALS = "All meals"
ALL_SOURCES = "All sources"
ALL_TAGS = "All tags"


def get_saved_tags():
    """Return every distinct tag the user has applied, alphabetically."""
    connection = create_connection()

    tags = pd.read_sql_query(
        "SELECT DISTINCT tag FROM food_tags ORDER BY tag COLLATE NOCASE",
        connection,
    )

    connection.close()
    return tags["tag"].tolist()


def set_entry_tags(entry_id, tags):
    """Replace the tags on one entry with the given list."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM food_tags WHERE entry_id = ?", (entry_id,))

    for tag in clean_tags(tags):
        cursor.execute(
            "INSERT OR IGNORE INTO food_tags (entry_id, tag) VALUES (?, ?)",
            (entry_id, tag),
        )

    connection.commit()
    connection.close()


def delete_food_entry(entry_id):
    """Delete one food entry and any tags attached to it."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM food_tags WHERE entry_id = ?", (entry_id,))
    cursor.execute("DELETE FROM food_log WHERE id = ?", (entry_id,))

    deleted_rows = cursor.rowcount
    connection.commit()
    connection.close()

    return deleted_rows


def save_protein_goal(day_type, daily_target_grams, fiber_target_grams=None):
    """Save or update the daily targets for a day type."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO protein_goals (day_type, daily_target_grams, fiber_target_grams)
        VALUES (?, ?, ?)
        ON CONFLICT(day_type)
        DO UPDATE SET
            daily_target_grams = excluded.daily_target_grams,
            fiber_target_grams = excluded.fiber_target_grams,
            updated_at = CURRENT_TIMESTAMP
        """,
        (day_type, daily_target_grams, fiber_target_grams),
    )

    connection.commit()
    connection.close()


def get_protein_goals():
    """Read all saved protein goals."""
    connection = create_connection()

    goals = pd.read_sql_query(
        """
        SELECT id, day_type, daily_target_grams, fiber_target_grams, updated_at
        FROM protein_goals
        """,
        connection,
    )

    connection.close()
    return goals


# Demo rows: description, protein, carbs, fat, fiber, calories, meal, source,
# date, tags. Tags here are only sample labels for the demo profile.
DEMO_ENTRIES = [
    ("Demo Greek yogurt", 18.0, 9.0, 4.0, 0.0, 150.0, "Breakfast", "Dairy",
     "2026-08-18", ["Dairy", "Low glycemic"]),
    ("Demo eggs (3)", 21.0, 1.5, 15.0, 0.0, 240.0, "Breakfast", "Eggs",
     "2026-08-18", ["Low glycemic"]),
    ("Demo grilled chicken breast", 35.0, 0.0, 12.0, 0.0, 280.0, "Lunch",
     "Meat/Poultry", "2026-08-18", ["Home cooked", "Low glycemic"]),
    ("Demo protein shake", 25.0, 6.0, 3.0, 1.0, 160.0, "Post-workout",
     "Protein powder", "2026-08-18", ["Processed"]),
    ("Demo lentil soup", 14.0, 30.0, 4.0, 11.0, 220.0, "Dinner",
     "Legumes/Beans", "2026-08-18", ["High fiber", "Plant-based", "Home cooked"]),
    ("Demo cottage cheese", 22.0, 6.0, 5.0, 0.0, 180.0, "Breakfast", "Dairy",
     "2026-08-19", ["Dairy", "Low glycemic"]),
    ("Demo salmon fillet", 34.0, 0.0, 18.0, 0.0, 300.0, "Dinner",
     "Fish/Seafood", "2026-08-19", ["Home cooked", "Low glycemic"]),
    ("Demo tofu stir-fry", 20.0, 22.0, 11.0, 6.0, 260.0, "Lunch",
     "Plant-based/Tofu", "2026-08-19", ["Plant-based", "High fiber"]),
    ("Demo almonds (handful)", 6.0, 6.0, 14.0, 3.5, 160.0, "Snack", "Other",
     "2026-08-19", ["High fiber", "Plant-based"]),
    ("Demo protein shake", 25.0, 6.0, 3.0, 1.0, 160.0, "Post-workout",
     "Protein powder", "2026-08-20", ["Processed"]),
    ("Demo turkey sandwich", 28.0, 38.0, 10.0, 5.0, 350.0, "Lunch",
     "Meat/Poultry", "2026-08-20", ["Whole grain", "Gluten"]),
    ("Demo skyr yogurt", 20.0, 8.0, 0.5, 0.0, 140.0, "Snack", "Dairy",
     "2026-08-20", ["Dairy", "Low glycemic"]),
    ("Demo chickpea curry", 16.0, 45.0, 9.0, 12.0, 300.0, "Dinner",
     "Legumes/Beans", "2026-08-20", ["High fiber", "Plant-based", "Home cooked"]),
]


def seed_dummy_data():
    """Add demo food entries and goals for portfolio demos.

    Demo rows saved by the protein-only version are topped up with macros and
    tags instead of being duplicated.
    """
    initialize_database()

    connection = create_connection()
    cursor = connection.cursor()

    for entry in DEMO_ENTRIES:
        (
            description,
            protein_grams,
            carbs_grams,
            fat_grams,
            fiber_grams,
            calories,
            meal_type,
            protein_source,
            log_date,
            tags,
        ) = entry

        existing = cursor.execute(
            "SELECT id FROM food_log WHERE description = ? AND log_date = ?",
            (description, log_date),
        ).fetchone()

        if existing:
            entry_id = existing[0]
            cursor.execute(
                """
                UPDATE food_log
                SET carbs_grams = ?, fat_grams = ?, fiber_grams = ?
                WHERE id = ?
                """,
                (carbs_grams, fat_grams, fiber_grams, entry_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO food_log (
                    description, protein_grams, calories, carbs_grams, fat_grams,
                    fiber_grams, meal_type, protein_source, log_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    description,
                    protein_grams,
                    calories,
                    carbs_grams,
                    fat_grams,
                    fiber_grams,
                    meal_type,
                    protein_source,
                    log_date,
                ),
            )
            entry_id = cursor.lastrowid

        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO food_tags (entry_id, tag) VALUES (?, ?)",
                (entry_id, tag),
            )

    demo_goals = [
        ("Rest day", 90.0, 25.0),
        ("Training day", 120.0, 30.0),
    ]

    cursor.executemany(
        """
        INSERT INTO protein_goals (day_type, daily_target_grams, fiber_target_grams)
        VALUES (?, ?, ?)
        ON CONFLICT(day_type)
        DO UPDATE SET
            daily_target_grams = excluded.daily_target_grams,
            fiber_target_grams = excluded.fiber_target_grams,
            updated_at = CURRENT_TIMESTAMP
        """,
        demo_goals,
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database tables are ready.")
