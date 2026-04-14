from core import get_engine
from db.models import (
    Base,
)
from db.migrations import (
    ensure_battery_checkout_columns,
    ensure_battery_history_columns,
    ensure_tba_match_battery_assignment_table,
    ensure_user_role_column,
)


def ensure_all_schemas():
    engine = get_engine()
    Base.metadata.create_all(engine)
    ensure_battery_checkout_columns(engine)
    ensure_battery_history_columns(engine)
    ensure_tba_match_battery_assignment_table(engine)
    ensure_user_role_column(engine)
    return engine
