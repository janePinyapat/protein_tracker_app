"""Tests for the SQLite layer, including the macro/tag migration.

Each test runs against a throwaway database file so the user's real
``protein_tracker.db`` is never touched.
"""

import sqlite3

import database


def create_legacy_database(database_path):
    """Recreate the protein-only schema that shipped before macros existed."""
    connection = sqlite3.connect(str(database_path))
    connection.executescript(
        """
        CREATE TABLE food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            protein_grams REAL NOT NULL,
            calories REAL,
            meal_type TEXT NOT NULL,
            protein_source TEXT NOT NULL,
            log_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE protein_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_type TEXT NOT NULL UNIQUE,
            daily_target_grams REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO food_log (description, protein_grams, calories, meal_type,
                              protein_source, log_date)
        VALUES ('Legacy chicken', 35.0, 280.0, 'Lunch', 'Meat/Poultry', '2026-08-18');
        INSERT INTO protein_goals (day_type, daily_target_grams)
        VALUES ('Rest day', 90.0);
        """
    )
    connection.commit()
    connection.close()


def test_clean_tags_trims_and_deduplicates():
    assert database.clean_tags(["  High fiber ", "High fiber", "Dairy"]) == [
        "High fiber",
        "Dairy",
    ]


def test_clean_tags_drops_blanks_and_none():
    assert database.clean_tags(["", "   ", None, "Dairy"]) == ["Dairy"]


def test_clean_tags_replaces_commas():
    """Tags are read back comma-joined, so a comma inside one would split it."""
    assert database.clean_tags(["Low carb, high fat"]) == ["Low carb  high fat"]


def test_clean_tags_handles_none():
    assert database.clean_tags(None) == []


def test_add_food_entry_saves_macros(temp_database):
    database.add_food_entry(
        description="Lentil soup",
        protein_grams=14.0,
        meal_type="Dinner",
        protein_source="Legumes/Beans",
        log_date="2026-08-20",
        calories=220.0,
        carbs_grams=30.0,
        fat_grams=4.0,
        fiber_grams=11.0,
    )

    entries = database.get_all_food_entries()
    row = entries.iloc[0]

    assert row["carbs_grams"] == 30.0
    assert row["fiber_grams"] == 11.0
    assert row["tags"] == ""


def test_add_food_entry_saves_tags(temp_database):
    database.add_food_entry(
        description="Lentil soup",
        protein_grams=14.0,
        meal_type="Dinner",
        protein_source="Legumes/Beans",
        log_date="2026-08-20",
        tags=["High fiber", "Plant-based"],
    )

    row = database.get_all_food_entries().iloc[0]
    assert sorted(row["tags"].split(", ")) == ["High fiber", "Plant-based"]


def test_get_saved_tags_returns_distinct_sorted_tags(temp_database):
    database.add_food_entry(
        "Soup", 14.0, "Dinner", "Legumes/Beans", "2026-08-20",
        tags=["High fiber", "Plant-based"],
    )
    database.add_food_entry(
        "Yogurt", 18.0, "Breakfast", "Dairy", "2026-08-20",
        tags=["Dairy", "High fiber"],
    )

    assert database.get_saved_tags() == ["Dairy", "High fiber", "Plant-based"]


def test_set_entry_tags_replaces_existing_tags(temp_database):
    entry_id = database.add_food_entry(
        "Soup", 14.0, "Dinner", "Legumes/Beans", "2026-08-20", tags=["High fiber"]
    )

    database.set_entry_tags(entry_id, ["Home cooked", "Plant-based"])

    row = database.get_all_food_entries().iloc[0]
    assert sorted(row["tags"].split(", ")) == ["Home cooked", "Plant-based"]


def test_delete_food_entry_removes_its_tags(temp_database):
    entry_id = database.add_food_entry(
        "Soup", 14.0, "Dinner", "Legumes/Beans", "2026-08-20", tags=["High fiber"]
    )

    database.delete_food_entry(entry_id)

    assert database.get_all_food_entries().empty
    assert database.get_saved_tags() == []


def test_get_filtered_food_entries_filters_by_tag(temp_database):
    database.add_food_entry(
        "Soup", 14.0, "Dinner", "Legumes/Beans", "2026-08-20", tags=["High fiber"]
    )
    database.add_food_entry(
        "Yogurt", 18.0, "Breakfast", "Dairy", "2026-08-20", tags=["Dairy"]
    )

    filtered = database.get_filtered_food_entries(tag="High fiber")

    assert len(filtered) == 1
    assert filtered.iloc[0]["description"] == "Soup"


def test_get_filtered_food_entries_combines_tag_and_meal(temp_database):
    database.add_food_entry(
        "Soup", 14.0, "Dinner", "Legumes/Beans", "2026-08-20", tags=["High fiber"]
    )
    database.add_food_entry(
        "Oats", 8.0, "Breakfast", "Other", "2026-08-20", tags=["High fiber"]
    )

    filtered = database.get_filtered_food_entries(tag="High fiber", meal_type="Dinner")

    assert len(filtered) == 1
    assert filtered.iloc[0]["description"] == "Soup"


def test_save_protein_goal_stores_fiber_target(temp_database):
    database.save_protein_goal("Rest day", 90.0, fiber_target_grams=25.0)

    goals = database.get_protein_goals()
    assert goals.iloc[0]["fiber_target_grams"] == 25.0


def test_save_protein_goal_updates_existing_day_type(temp_database):
    database.save_protein_goal("Rest day", 90.0, 25.0)
    database.save_protein_goal("Rest day", 110.0, 30.0)

    goals = database.get_protein_goals()
    assert len(goals) == 1
    assert goals.iloc[0]["daily_target_grams"] == 110.0


def test_get_user_profile_returns_none_before_onboarding(temp_database):
    assert database.get_user_profile() is None


def test_save_user_profile_round_trips(temp_database):
    database.save_user_profile(
        "Vegetarian", ["PCOS management", "General health tracking"]
    )

    profile = database.get_user_profile()

    assert profile["diet_type"] == "Vegetarian"
    assert profile["purposes"] == ["PCOS management", "General health tracking"]


def test_save_user_profile_updates_the_single_row(temp_database):
    database.save_user_profile("Omnivore", ["Other"])
    database.save_user_profile("Vegan", ["Strength training / muscle recovery"])

    profile = database.get_user_profile()
    assert profile["diet_type"] == "Vegan"
    assert profile["purposes"] == ["Strength training / muscle recovery"]


def test_save_user_profile_handles_empty_purposes(temp_database):
    database.save_user_profile("Omnivore", [])

    profile = database.get_user_profile()
    assert profile["purposes"] == []


def test_save_user_profile_stores_weight(temp_database):
    database.save_user_profile(
        "Vegan", ["Strength training / muscle recovery"], 68.0, "kg"
    )

    profile = database.get_user_profile()
    assert profile["weight_value"] == 68.0
    assert profile["weight_unit"] == "kg"


def test_save_user_profile_defaults_weight_to_none(temp_database):
    database.save_user_profile("Omnivore", ["Other"])

    profile = database.get_user_profile()
    assert profile["weight_value"] is None
    assert profile["weight_unit"] is None


def test_save_user_profile_stores_height(temp_database):
    database.save_user_profile(
        "Vegan", ["Strength training / muscle recovery"], 68.0, "kg", 170.0, "cm"
    )

    profile = database.get_user_profile()
    assert profile["height_value"] == 170.0
    assert profile["height_unit"] == "cm"


def test_save_user_profile_defaults_height_to_none(temp_database):
    database.save_user_profile("Omnivore", ["Other"], 68.0, "kg")

    profile = database.get_user_profile()
    assert profile["height_value"] is None
    assert profile["height_unit"] is None


def test_migration_adds_weight_columns_to_legacy_user_profile(tmp_path, monkeypatch):
    """A profile saved before weight tracking existed must survive the
    migration and keep working — weight just comes back as None."""
    database_path = tmp_path / "legacy_profile.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    connection = sqlite3.connect(str(database_path))
    connection.executescript(
        """
        CREATE TABLE user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            diet_type TEXT NOT NULL,
            purposes TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO user_profile (id, diet_type, purposes) VALUES (1, 'Omnivore', 'Other');
        """
    )
    connection.commit()
    connection.close()

    database.initialize_database()

    profile = database.get_user_profile()
    assert profile["diet_type"] == "Omnivore"
    assert profile["weight_value"] is None
    assert profile["height_value"] is None

    database.save_user_profile("Omnivore", ["Other"], 70.0, "kg", 170.0, "cm")
    updated = database.get_user_profile()
    assert updated["weight_value"] == 70.0
    assert updated["height_value"] == 170.0


def test_migration_adds_height_columns_to_weight_only_user_profile(
    tmp_path, monkeypatch
):
    """A profile saved after weight tracking existed but before height did
    must survive the migration and keep working — height comes back as
    None."""
    database_path = tmp_path / "weight_only_profile.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    connection = sqlite3.connect(str(database_path))
    connection.executescript(
        """
        CREATE TABLE user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            diet_type TEXT NOT NULL,
            purposes TEXT NOT NULL,
            weight_value REAL,
            weight_unit TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO user_profile (id, diet_type, purposes, weight_value, weight_unit)
        VALUES (1, 'Vegan', 'Strength training / muscle recovery', 65.0, 'kg');
        """
    )
    connection.commit()
    connection.close()

    database.initialize_database()

    profile = database.get_user_profile()
    assert profile["weight_value"] == 65.0
    assert profile["height_value"] is None


def test_migration_adds_macro_columns_to_legacy_database(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    create_legacy_database(database_path)
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    database.initialize_database()

    entries = database.get_all_food_entries()
    row = entries.iloc[0]

    assert row["description"] == "Legacy chicken"
    assert row["protein_grams"] == 35.0
    assert row["carbs_grams"] is None or pd_isna(row["carbs_grams"])


def test_migration_preserves_legacy_goals(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    create_legacy_database(database_path)
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    database.initialize_database()

    goals = database.get_protein_goals()
    assert goals.iloc[0]["daily_target_grams"] == 90.0
    assert "fiber_target_grams" in goals.columns


def test_migration_is_idempotent(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    create_legacy_database(database_path)
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    database.initialize_database()
    database.initialize_database()
    database.migrate_database()

    assert len(database.get_all_food_entries()) == 1


def test_seed_dummy_data_is_idempotent(temp_database):
    database.seed_dummy_data()
    first_count = len(database.get_all_food_entries())

    database.seed_dummy_data()
    second_count = len(database.get_all_food_entries())

    assert first_count == second_count == len(database.DEMO_ENTRIES)


def test_seed_dummy_data_backfills_legacy_demo_rows(tmp_path, monkeypatch):
    """Demo rows saved without macros get topped up, not duplicated."""
    database_path = tmp_path / "legacy_demo.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))
    database.initialize_database()

    database.add_food_entry(
        description="Demo lentil soup",
        protein_grams=14.0,
        meal_type="Dinner",
        protein_source="Legumes/Beans",
        log_date="2026-08-18",
        calories=220.0,
    )

    database.seed_dummy_data()

    entries = database.get_all_food_entries()
    soup = entries[entries["description"] == "Demo lentil soup"]

    assert len(soup) == 1
    assert soup.iloc[0]["fiber_grams"] == 11.0


def pd_isna(value):
    import pandas as pd

    return pd.isna(value)
