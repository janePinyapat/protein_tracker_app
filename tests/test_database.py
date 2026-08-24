"""Tests for the SQLite layer, including the macro/tag migration.

Each test runs against a throwaway database file so the user's real
``protein_tracker.db`` is never touched.
"""

import sqlite3
from datetime import date, timedelta

import pandas as pd

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


def test_get_meal_recommendations_returns_empty_before_generation(temp_database):
    assert database.get_meal_recommendations("2026-08-23").empty


def test_save_meal_recommendations_round_trips(temp_database):
    meals = [
        {
            "meal_type": "Breakfast",
            "recipe_id": 111,
            "meal_name": "Yogurt bowl",
            "description": "Yogurt with berries.",
            "protein_grams": 25.0,
            "fiber_grams": 6.0,
            "calories": 350.0,
            "source_title": "Example",
            "source_url": "https://example.com/yogurt",
            "image_url": "https://img.spoonacular.com/recipes/yogurt.jpg",
        },
        {
            "meal_type": "Lunch",
            "recipe_id": 222,
            "meal_name": "Lentil salad",
            "description": "Lentils and greens.",
            "protein_grams": 22.0,
            "fiber_grams": 14.0,
            "calories": 420.0,
            "source_title": "Example",
            "source_url": "https://example.com/lentils",
            "image_url": "https://img.spoonacular.com/recipes/lentils.jpg",
        },
    ]

    database.save_meal_recommendations("2026-08-23", meals)

    saved = database.get_meal_recommendations("2026-08-23")
    assert len(saved) == 2
    assert list(saved["meal_type"]) == ["Breakfast", "Lunch"]  # meal-type order
    assert saved.iloc[0]["meal_name"] == "Yogurt bowl"
    assert saved.iloc[0]["protein_grams"] == 25.0
    assert saved.iloc[0]["recipe_id"] == 111
    assert saved.iloc[0]["image_url"] == "https://img.spoonacular.com/recipes/yogurt.jpg"


def test_save_meal_recommendations_defaults_image_url_to_none(temp_database):
    database.save_meal_recommendations(
        "2026-08-23",
        [{"meal_type": "Breakfast", "meal_name": "No image given", "protein_grams": 10.0}],
    )

    saved = database.get_meal_recommendations("2026-08-23")
    assert pd.isna(saved.iloc[0]["image_url"])


def test_save_meal_recommendations_defaults_recipe_id_to_none(temp_database):
    database.save_meal_recommendations(
        "2026-08-23",
        [{"meal_type": "Breakfast", "meal_name": "No id given", "protein_grams": 10.0}],
    )

    saved = database.get_meal_recommendations("2026-08-23")
    assert pd.isna(saved.iloc[0]["recipe_id"])


def test_get_recent_recommended_recipe_ids_returns_ids_since_cutoff(temp_database):
    database.save_meal_recommendations(
        "2026-08-10",
        [{"meal_type": "Breakfast", "recipe_id": 1, "meal_name": "Old", "protein_grams": 10.0}],
    )
    database.save_meal_recommendations(
        "2026-08-20",
        [
            {"meal_type": "Breakfast", "recipe_id": 2, "meal_name": "Recent A", "protein_grams": 10.0},
            {"meal_type": "Lunch", "recipe_id": 3, "meal_name": "Recent B", "protein_grams": 10.0},
        ],
    )

    recent_ids = database.get_recent_recommended_recipe_ids("2026-08-15")

    assert set(recent_ids) == {2, 3}


def test_get_recent_recommended_recipe_ids_skips_rows_without_a_recipe_id(
    temp_database,
):
    database.save_meal_recommendations(
        "2026-08-23",
        [{"meal_type": "Breakfast", "meal_name": "No id", "protein_grams": 10.0}],
    )

    assert database.get_recent_recommended_recipe_ids("2026-08-01") == []


def test_get_recent_recommended_recipe_ids_returns_empty_list_when_none_saved(
    temp_database,
):
    assert database.get_recent_recommended_recipe_ids("2026-08-01") == []


def test_save_meal_recommendations_only_affects_its_own_date(temp_database):
    database.save_meal_recommendations(
        "2026-08-22",
        [
            {
                "meal_type": "Dinner",
                "meal_name": "Yesterday's dinner",
                "protein_grams": 30.0,
                "fiber_grams": 5.0,
            }
        ],
    )
    database.save_meal_recommendations(
        "2026-08-23",
        [
            {
                "meal_type": "Dinner",
                "meal_name": "Today's dinner",
                "protein_grams": 40.0,
                "fiber_grams": 10.0,
            }
        ],
    )

    assert database.get_meal_recommendations("2026-08-22").iloc[0]["meal_name"] == (
        "Yesterday's dinner"
    )
    assert database.get_meal_recommendations("2026-08-23").iloc[0]["meal_name"] == (
        "Today's dinner"
    )


def test_save_meal_recommendations_replaces_existing_rows_for_same_date(
    temp_database,
):
    database.save_meal_recommendations(
        "2026-08-23",
        [{"meal_type": "Breakfast", "meal_name": "Old idea", "protein_grams": 10.0}],
    )
    database.save_meal_recommendations(
        "2026-08-23",
        [{"meal_type": "Breakfast", "meal_name": "New idea", "protein_grams": 20.0}],
    )

    saved = database.get_meal_recommendations("2026-08-23")
    assert len(saved) == 1
    assert saved.iloc[0]["meal_name"] == "New idea"


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


def test_migration_adds_recipe_id_column_to_legacy_meal_recommendations(
    tmp_path, monkeypatch
):
    """A cached recommendation saved before recipe_id existed must survive
    the migration and keep working — recipe_id just comes back as None,
    never mistaken for a real id worth excluding from future searches."""
    database_path = tmp_path / "legacy_meal_recommendations.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    connection = sqlite3.connect(str(database_path))
    connection.executescript(
        """
        CREATE TABLE meal_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rec_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            meal_name TEXT NOT NULL,
            description TEXT,
            protein_grams REAL,
            fiber_grams REAL,
            calories REAL,
            source_title TEXT,
            source_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (rec_date, meal_type)
        );
        INSERT INTO meal_recommendations (rec_date, meal_type, meal_name, protein_grams)
        VALUES ('2026-08-20', 'Breakfast', 'Legacy Yogurt Bowl', 20.0);
        """
    )
    connection.commit()
    connection.close()

    database.initialize_database()

    saved = database.get_meal_recommendations("2026-08-20")
    assert saved.iloc[0]["meal_name"] == "Legacy Yogurt Bowl"
    assert pd.isna(saved.iloc[0]["recipe_id"])
    assert database.get_recent_recommended_recipe_ids("2026-08-01") == []


def test_migration_adds_image_url_column_to_legacy_meal_recommendations(
    tmp_path, monkeypatch
):
    """A cached recommendation saved before image_url existed must survive
    the migration and keep working — image_url just comes back as None."""
    database_path = tmp_path / "legacy_meal_recommendations_image.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))

    connection = sqlite3.connect(str(database_path))
    connection.executescript(
        """
        CREATE TABLE meal_recommendations (
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
        );
        INSERT INTO meal_recommendations (rec_date, meal_type, meal_name, protein_grams)
        VALUES ('2026-08-20', 'Breakfast', 'Legacy Yogurt Bowl', 20.0);
        """
    )
    connection.commit()
    connection.close()

    database.initialize_database()

    saved = database.get_meal_recommendations("2026-08-20")
    assert saved.iloc[0]["meal_name"] == "Legacy Yogurt Bowl"
    assert pd.isna(saved.iloc[0]["image_url"])


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
    anchor = date(2026, 8, 24)

    database.seed_dummy_data(anchor_date=anchor)
    first_food_count = len(database.get_all_food_entries())
    first_water_count = len(database.get_all_water_entries())
    first_sleep_count = len(database.get_all_sleep_entries())

    database.seed_dummy_data(anchor_date=anchor)

    assert len(database.get_all_food_entries()) == first_food_count
    assert len(database.get_all_water_entries()) == first_water_count
    assert len(database.get_all_sleep_entries()) == first_sleep_count
    assert first_food_count == len(database.build_demo_food_entries(anchor))


def test_seed_dummy_data_backfills_legacy_demo_rows(tmp_path, monkeypatch):
    """Demo rows saved without macros get topped up, not duplicated."""
    database_path = tmp_path / "legacy_demo.db"
    monkeypatch.setattr(database, "DATABASE_NAME", str(database_path))
    database.initialize_database()

    anchor = date(2026, 8, 24)
    (
        description, _protein, _carbs, _fat, fiber_grams, calories,
        meal_type, protein_source, log_date, _tags,
    ) = database.build_demo_food_entries(anchor)[0]

    database.add_food_entry(
        description=description,
        protein_grams=1.0,
        meal_type=meal_type,
        protein_source=protein_source,
        log_date=log_date,
        calories=calories,
    )

    database.seed_dummy_data(anchor_date=anchor)

    entries = database.get_all_food_entries()
    matching = entries[
        (entries["description"] == description) & (entries["log_date"] == log_date)
    ]

    assert len(matching) == 1
    assert matching.iloc[0]["fiber_grams"] == fiber_grams


def test_seed_dummy_data_covers_three_weeks(temp_database):
    anchor = date(2026, 8, 24)
    database.seed_dummy_data(anchor_date=anchor)

    food_entries = database.get_all_food_entries()
    water_entries = database.get_all_water_entries()
    sleep_entries = database.get_all_sleep_entries()

    window_start = (anchor - timedelta(days=database.DEMO_DAYS - 1)).isoformat()

    assert food_entries["log_date"].nunique() == database.DEMO_DAYS
    assert water_entries["log_date"].nunique() == database.DEMO_DAYS
    assert len(sleep_entries) == database.DEMO_DAYS
    assert food_entries["log_date"].min() == window_start
    assert food_entries["log_date"].max() == anchor.isoformat()


def test_seed_dummy_data_sets_wellness_goals_and_profile_when_unset(temp_database):
    database.seed_dummy_data(anchor_date=date(2026, 8, 24))

    goals = database.get_wellness_goals()
    profile = database.get_user_profile()

    assert goals["water_target_ml"] == database.DEMO_WATER_TARGET_ML
    assert goals["sleep_target_hours"] == database.DEMO_SLEEP_TARGET_HOURS
    assert profile["diet_type"] == "Omnivore"


def test_seed_dummy_data_preserves_existing_profile_and_goals(temp_database):
    database.save_user_profile("Vegan", ["PCOS management"], 60.0, "kg")
    database.save_wellness_goals(water_target_ml=1800.0, sleep_target_hours=9.0)

    database.seed_dummy_data(anchor_date=date(2026, 8, 24))

    profile = database.get_user_profile()
    goals = database.get_wellness_goals()

    assert profile["diet_type"] == "Vegan"
    assert goals["water_target_ml"] == 1800.0
    assert goals["sleep_target_hours"] == 9.0


def test_seed_dummy_data_sets_protein_goals(temp_database):
    database.seed_dummy_data(anchor_date=date(2026, 8, 24))

    goals = database.get_protein_goals()
    rest_goal = goals[goals["day_type"] == "Rest day"].iloc[0]
    training_goal = goals[goals["day_type"] == "Training day"].iloc[0]

    assert rest_goal["daily_target_grams"] == 90.0
    assert training_goal["daily_target_grams"] == 120.0


def pd_isna(value):
    import pandas as pd

    return pd.isna(value)


# --- water_log -----------------------------------------------------------------


def test_add_water_entry_and_get_all_water_entries(temp_database):
    database.add_water_entry(250.0, "2026-08-20")
    database.add_water_entry(500.0, "2026-08-20")

    entries = database.get_all_water_entries()
    assert len(entries) == 2
    assert set(entries["amount_ml"]) == {250.0, 500.0}


def test_get_all_water_entries_returns_empty_before_logging(temp_database):
    assert database.get_all_water_entries().empty


def test_delete_water_entry_removes_only_that_row(temp_database):
    first_id = database.add_water_entry(250.0, "2026-08-20")
    database.add_water_entry(500.0, "2026-08-20")

    deleted = database.delete_water_entry(first_id)

    assert deleted == 1
    remaining = database.get_all_water_entries()
    assert len(remaining) == 1
    assert remaining.iloc[0]["amount_ml"] == 500.0


def test_delete_water_entry_returns_zero_for_unknown_id(temp_database):
    assert database.delete_water_entry(999) == 0


# --- sleep_log -----------------------------------------------------------------


def test_save_sleep_entry_round_trips(temp_database):
    database.save_sleep_entry("2026-08-20", 7.5, "Restful")

    entry = database.get_sleep_entry("2026-08-20")
    assert entry["hours_slept"] == 7.5
    assert entry["notes"] == "Restful"


def test_get_sleep_entry_returns_none_when_not_logged(temp_database):
    assert database.get_sleep_entry("2026-08-20") is None


def test_save_sleep_entry_upserts_instead_of_duplicating(temp_database):
    database.save_sleep_entry("2026-08-20", 6.0, None)
    database.save_sleep_entry("2026-08-20", 8.0, "Better night")

    all_entries = database.get_all_sleep_entries()
    assert len(all_entries) == 1
    assert all_entries.iloc[0]["hours_slept"] == 8.0
    assert all_entries.iloc[0]["notes"] == "Better night"


def test_get_all_sleep_entries_orders_most_recent_first(temp_database):
    database.save_sleep_entry("2026-08-18", 7.0)
    database.save_sleep_entry("2026-08-20", 6.5)

    entries = database.get_all_sleep_entries()
    assert list(entries["log_date"]) == ["2026-08-20", "2026-08-18"]


def test_delete_sleep_entry_removes_that_date(temp_database):
    database.save_sleep_entry("2026-08-20", 7.0)

    deleted = database.delete_sleep_entry("2026-08-20")

    assert deleted == 1
    assert database.get_sleep_entry("2026-08-20") is None


# --- wellness_goals --------------------------------------------------------------


def test_get_wellness_goals_returns_none_before_saving(temp_database):
    assert database.get_wellness_goals() is None


def test_save_wellness_goals_round_trips_both_targets(temp_database):
    database.save_wellness_goals(water_target_ml=2000.0, sleep_target_hours=8.0)

    goals = database.get_wellness_goals()
    assert goals["water_target_ml"] == 2000.0
    assert goals["sleep_target_hours"] == 8.0


def test_save_wellness_goals_allows_setting_only_one_target(temp_database):
    database.save_wellness_goals(water_target_ml=2000.0, sleep_target_hours=None)

    goals = database.get_wellness_goals()
    assert goals["water_target_ml"] == 2000.0
    assert goals["sleep_target_hours"] is None


def test_save_wellness_goals_updates_the_single_row(temp_database):
    database.save_wellness_goals(water_target_ml=2000.0, sleep_target_hours=8.0)
    database.save_wellness_goals(water_target_ml=2500.0, sleep_target_hours=7.0)

    goals = database.get_wellness_goals()
    assert goals["water_target_ml"] == 2500.0
    assert goals["sleep_target_hours"] == 7.0
