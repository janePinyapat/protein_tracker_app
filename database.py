import sqlite3

import pandas as pd


DATABASE_NAME = "protein_tracker.db"


def create_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)


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
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def add_food_entry(
    description,
    protein_grams,
    meal_type,
    protein_source,
    log_date,
    calories=None,
):
    """Save one food log entry."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO food_log (
            description, protein_grams, calories, meal_type, protein_source, log_date
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (description, protein_grams, calories, meal_type, protein_source, log_date),
    )

    connection.commit()
    connection.close()


def get_all_food_entries():
    """Read all saved food entries from the database."""
    connection = create_connection()

    food_entries = pd.read_sql_query(
        """
        SELECT id, description, protein_grams, calories, meal_type,
               protein_source, log_date, created_at
        FROM food_log
        ORDER BY log_date DESC, id DESC
        """,
        connection,
    )

    connection.close()
    return food_entries


def get_filtered_food_entries(log_date=None, meal_type=None, protein_source=None):
    """Read food entries filtered by date, meal type, and protein source."""
    connection = create_connection()

    query = """
        SELECT id, description, protein_grams, calories, meal_type,
               protein_source, log_date, created_at
        FROM food_log
        WHERE 1 = 1
    """
    parameters = []

    if log_date:
        query += " AND log_date = ?"
        parameters.append(str(log_date))

    if meal_type and meal_type != "All meals":
        query += " AND meal_type = ?"
        parameters.append(meal_type)

    if protein_source and protein_source != "All sources":
        query += " AND protein_source = ?"
        parameters.append(protein_source)

    query += " ORDER BY log_date DESC, id DESC"

    food_entries = pd.read_sql_query(query, connection, params=parameters)

    connection.close()
    return food_entries


def delete_food_entry(entry_id):
    """Delete one food entry by its id."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM food_log WHERE id = ?", (entry_id,))

    deleted_rows = cursor.rowcount
    connection.commit()
    connection.close()

    return deleted_rows


def save_protein_goal(day_type, daily_target_grams):
    """Save or update the daily protein target for a day type."""
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO protein_goals (day_type, daily_target_grams)
        VALUES (?, ?)
        ON CONFLICT(day_type)
        DO UPDATE SET
            daily_target_grams = excluded.daily_target_grams,
            updated_at = CURRENT_TIMESTAMP
        """,
        (day_type, daily_target_grams),
    )

    connection.commit()
    connection.close()


def get_protein_goals():
    """Read all saved protein goals."""
    connection = create_connection()

    goals = pd.read_sql_query(
        "SELECT id, day_type, daily_target_grams, updated_at FROM protein_goals",
        connection,
    )

    connection.close()
    return goals


def seed_dummy_data():
    """Add demo food entries and protein goals for portfolio demos."""
    create_food_log_table()
    create_protein_goals_table()

    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM food_log WHERE description LIKE 'Demo %'")
    demo_count = cursor.fetchone()[0]

    if demo_count == 0:
        demo_entries = [
            ("Demo Greek yogurt", 18.0, 150.0, "Breakfast", "Dairy", "2026-08-18"),
            ("Demo eggs (3)", 21.0, 240.0, "Breakfast", "Eggs", "2026-08-18"),
            ("Demo grilled chicken breast", 35.0, 280.0, "Lunch", "Meat/Poultry", "2026-08-18"),
            ("Demo protein shake", 25.0, 160.0, "Post-workout", "Protein powder", "2026-08-18"),
            ("Demo lentil soup", 14.0, 220.0, "Dinner", "Legumes/Beans", "2026-08-18"),
            ("Demo cottage cheese", 22.0, 180.0, "Breakfast", "Dairy", "2026-08-19"),
            ("Demo salmon fillet", 34.0, 300.0, "Dinner", "Fish/Seafood", "2026-08-19"),
            ("Demo tofu stir-fry", 20.0, 260.0, "Lunch", "Plant-based/Tofu", "2026-08-19"),
            ("Demo almonds (handful)", 6.0, 160.0, "Snack", "Other", "2026-08-19"),
            ("Demo protein shake", 25.0, 160.0, "Post-workout", "Protein powder", "2026-08-20"),
            ("Demo turkey sandwich", 28.0, 350.0, "Lunch", "Meat/Poultry", "2026-08-20"),
            ("Demo skyr yogurt", 20.0, 140.0, "Snack", "Dairy", "2026-08-20"),
            ("Demo chickpea curry", 16.0, 300.0, "Dinner", "Legumes/Beans", "2026-08-20"),
        ]

        cursor.executemany(
            """
            INSERT INTO food_log (
                description, protein_grams, calories, meal_type, protein_source, log_date
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            demo_entries,
        )

    demo_goals = [
        ("Rest day", 90.0),
        ("Training day", 120.0),
    ]

    cursor.executemany(
        """
        INSERT INTO protein_goals (day_type, daily_target_grams)
        VALUES (?, ?)
        ON CONFLICT(day_type)
        DO UPDATE SET
            daily_target_grams = excluded.daily_target_grams,
            updated_at = CURRENT_TIMESTAMP
        """,
        demo_goals,
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_food_log_table()
    create_protein_goals_table()
    print("Database tables are ready.")
