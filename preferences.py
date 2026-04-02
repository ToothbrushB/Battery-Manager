"""
Centralized preferences/settings management module.
Provides functions for reading and writing application preferences.
"""
import json
import os
from typing import Optional
import sqlalchemy
from models import PreferenceDb, FieldMappingDb

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))


def get_preference(key: str) -> Optional[str]:
    """
    Get a preference value by key.
    
    Args:
        key: The preference key to retrieve
        
    Returns:
        The preference value as a string, or None if not found
    """
    with sqlalchemy.orm.Session(engine) as session:
        pref = session.get(PreferenceDb, key)
        return pref.value if pref else None


def get_allowed_checkout_assets() -> list[dict[str, str]]:
    """Parse the allowed checkout assets preference into id/name pairs."""

    raw = get_preference("asset-checkout-allowed") or ""
    assets: list[dict[str, str]] = []
    for entry in raw.split(","):
        token = entry.strip()
        if not token:
            continue
        if ":" in token:
            asset_id, name = token.split(":", 1)
        else:
            asset_id, name = token, ""
        asset_id = asset_id.strip()
        name = name.strip()
        if asset_id:
            assets.append({"id": asset_id, "name": name})
    return assets


def get_hidden_asset_ids() -> set[int]:
    """Parse hidden battery asset IDs from preference storage."""

    raw = get_preference("hidden-asset-ids") or ""
    hidden_ids: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            hidden_ids.add(int(token))
        except ValueError:
            continue
    return hidden_ids


def set_preference(key: str, value: str) -> None:
    """
    Set a preference value. Creates the preference if it doesn't exist,
    updates it if it does.
    
    Args:
        key: The preference key
        value: The value to set
    """
    with sqlalchemy.orm.Session(engine) as session:
        pref = session.get(PreferenceDb, key)
        if pref:
            pref.value = value
        else:
            session.add(PreferenceDb(key=key, value=str(value)))
        session.commit()


def load_settings_from_config(config_path: str = "config.json") -> None:
    """
    Load settings from config file and initialize database with defaults.
    This function ensures all settings from the config file exist in the database.
    
    Args:
        config_path: Path to the configuration JSON file
    """
    config = json.load(open(config_path))
    
    default_mappings = [
FieldMappingDb(
                name="Battery Usage Type",
                db_column_name="",
            ),
            FieldMappingDb(
                name="Battery Voltage Curve",
                db_column_name="",
            ),
            FieldMappingDb(
                name="Battery Cycle Count",
                db_column_name="",
            )
    ]
    with sqlalchemy.orm.Session(engine) as session:
        # Initialize field mappings if they don't exist
        existing_mappings = session.query(FieldMappingDb).all()
        for default in default_mappings:
            if not any(m.name == default.name for m in existing_mappings):
                session.add(default)
        
        # Initialize preferences from config
        existing_settings = session.query(PreferenceDb).all()
        existing_keys = {s.key for s in existing_settings}
        
        for section in config:
            for setting in section["settings"]:
                if setting["id"] not in existing_keys:
                    session.add(PreferenceDb(key=setting["id"], value=str(setting["value"])))
        
        session.commit()


def get_all_preferences() -> dict[str, str]:
    """
    Get all preferences as a dictionary.
    
    Returns:
        Dictionary mapping preference keys to values
    """
    with sqlalchemy.orm.Session(engine) as session:
        prefs = session.query(PreferenceDb).all()
        return {pref.key: pref.value for pref in prefs}


def update_preferences_from_dict(preferences: dict[str, str]) -> None:
    """
    Update multiple preferences at once from a dictionary.
    
    Args:
        preferences: Dictionary mapping preference keys to new values
    """
    with sqlalchemy.orm.Session(engine) as session:
        for key, value in preferences.items():
            pref = session.get(PreferenceDb, key)
            if pref:
                pref.value = value
            else:
                session.add(PreferenceDb(key=key, value=str(value)))
        session.commit()
