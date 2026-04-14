from __future__ import annotations
from datetime import datetime
import enum
from typing import Optional, Generic, TypeVar
import msgspec
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

T = TypeVar("T")


class Paginated(msgspec.Struct, Generic[T]):  # copied from msgspec docs
    """A generic paginated API wrapper, parametrized by the item type."""

    total: int  # The total number of items found
    rows: list[T]  # Items returned, up to `per_page` in length


class DateTime(msgspec.Struct):
    datetime: str
    formatted: str


class Date(msgspec.Struct):
    date: str
    formatted: str


# class AvailableActions(msgspec.Struct):
#     update: bool
#     delete: bool
#     bulk_selectable: AvailableActions
#     clone: bool
#     restore: bool
class Company(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class Department(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class User(msgspec.Struct):
    id: int
    name: str
    username: Optional[str] = None
    avatar: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    remote: Optional[str] = None
    locale: Optional[str] = None
    employee_number: Optional[str] = None
    manager: Optional[User] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    email: Optional[str] = None
    department: Optional[Department] = None
    department_manager: Optional[User] = None
    location: Optional[Location] = None
    notes: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[dict] = None
    activated: Optional[bool] = False
    autoassign_licenses: Optional[bool] = False
    ldap_import: Optional[bool] = False
    two_factor_enrolled: Optional[bool] = False
    two_factor_optin: Optional[bool] = False
    assets_count: Optional[int] = 0
    licenses_count: Optional[int] = 0
    accessories_count: Optional[int] = 0
    consumables_count: Optional[int] = 0
    manages_users_count: Optional[int] = 0
    manages_locations_count: Optional[int] = 0
    company: Optional[Company] = None
    created_by: Optional[User] = None
    created_at: Optional[DateTime] = None
    updated_at: Optional[DateTime] = None
    start_date: Optional[DateTime] = None
    end_date: Optional[DateTime] = None
    last_login: Optional[DateTime] = None
    deleted_at: Optional[DateTime] = None
    groups: Optional[list[str]] = None


class Location(msgspec.Struct):
    id: int
    name: Optional[str] = None
    children: Optional[list[Location]] = None
    image: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    accessories_count: Optional[int] = None
    assigned_accessories_count: Optional[int] = None
    assets_count: Optional[int] = None
    rtd_assets_count: Optional[int] = None
    users_count: Optional[int] = None
    consumables_count: Optional[int] = None
    children_count: Optional[int] = None
    currency: Optional[str] = None
    ldap_ou: Optional[str] = None
    tag_color: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[DateTime] = None
    updated_at: Optional[DateTime] = None
    parent: Optional[Location] = None
    manager: Optional[User] = None
    allowed: Optional[bool] = None


class Model(msgspec.Struct):
    id: int
    name: str


class StatusLabelAsset(msgspec.Struct):
    id: int
    name: Optional[str] = None
    status_type: Optional[str] = None
    status_meta: Optional[str] = None


class Category(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class Manufacturer(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class Supplier(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class Depreciation(msgspec.Struct):
    id: int
    name: str
    months: int
    type: str
    minimum: Optional[float] = None


class Assignee(msgspec.Struct):
    id: int
    name: Optional[str] = None
    type: Optional[str] = None


class CustomField(msgspec.Struct):
    id: int
    name: str
    db_column_name: str
    format: Optional[str] = None
    field_values: Optional[str] = None
    field_values_array: Optional[list[str]] = None
    type: Optional[str] = None
    required: Optional[bool] = None
    display_in_user_view: Optional[bool] = None
    auto_add_to_fieldsets: Optional[bool] = None
    show_in_listview: Optional[bool] = None
    display_checkin: Optional[bool] = None
    display_audit: Optional[bool] = None
    created_at: Optional[DateTime] = None
    updated_at: Optional[DateTime] = None
    config: Optional[CustomFieldConfig] = None


class CustomFieldAsset(msgspec.Struct):
    field: str
    value: Optional[str] = None
    field_format: Optional[str] = None
    element: Optional[str] = None
    custom_field: Optional[CustomField] = None


class StatusLabel(msgspec.Struct):
    id: int
    name: str
    type: str
    color: Optional[str] = None
    show_in_nav: Optional[bool] = None
    default_label: Optional[bool] = None
    assets_counts: Optional[int] = None
    notes: Optional[str] = None
    created_by: Optional[User] = None
    created_at: Optional[DateTime] = None
    updated_at: Optional[DateTime] = None
    allowed: Optional[bool] = None


class Asset(msgspec.Struct):
    id: int
    name: str
    asset_tag: str
    status_label: StatusLabelAsset
    category: Category
    model: Model
    company: Optional[Company] = None
    serial: Optional[str] = None
    byod: Optional[bool] = None
    requestable: Optional[bool] = None
    model_number: Optional[str] = None
    eol: Optional[str] = None
    asset_eol_date: Optional[DateTime] = None
    manufacturer: Optional[Manufacturer] = None
    supplier: Optional[Supplier] = None
    depreciation: Optional[Depreciation] = None
    notes: Optional[str] = None
    order_number: Optional[str] = None
    location: Optional[Location] = None
    image: Optional[str] = None
    qr: Optional[str] = None
    alt_barcode: Optional[str] = None
    assigned_to: Optional[Assignee] = None
    warranty_months: Optional[str] = None
    warranty_expires: Optional[str] = None
    created_at: Optional[DateTime] = None
    created_by: Optional[User] = None
    updated_at: Optional[DateTime] = None
    last_audit_date: Optional[DateTime] = None
    next_audit_date: Optional[Date] = None
    purchased_date: Optional[DateTime] = None
    age: Optional[str] = None
    last_checkout: Optional[DateTime] = None
    last_checkin: Optional[DateTime] = None
    expected_checkin: Optional[Date] = None
    purchase_cost: Optional[float] = None
    custom_fields: Optional[dict[str, CustomFieldAsset]] = None
    

class Base(DeclarativeBase):
    pass

class UserDb(Base):
    __tablename__ = "user"
    username: Mapped[str] = mapped_column(String(255), primary_key=True)
    password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Optional[str]] = mapped_column(String(50), default="viewer")

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, role={self.role!r})"
    
class LocationDb(Base):
    __tablename__ = "location"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    allowed: Mapped[Optional[bool]] = mapped_column(default=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("location.id"))
    is_parent: Mapped[bool] = mapped_column(default=False)
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"Location(id={self.id!r}, name={self.name!r})"

    @classmethod
    def fromLocation(cls, location: Location, existing: LocationDb = None) -> LocationDb:
        obj = existing if existing else cls()
        obj.id = location.id
        obj.name = location.name
        obj.parent_id = location.parent.id if location.parent else None
        obj.is_parent = True if location.children else False
        obj.remote_data = msgspec.msgpack.encode(location)
        obj.last_synced_at = datetime.now().timestamp()
        return obj
class CustomFieldConfig(enum.Enum):
    HIDE = "hide"
    DISPLAY = "display"
    EDIT = "edit"


class CustomFieldDb(Base):
    __tablename__ = "custom_field"
    db_column_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    config: Mapped[CustomFieldConfig] = mapped_column(
        String(50), default=CustomFieldConfig.HIDE.value
    )
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self) -> str:
        return (
            f"CustomField(db_column_name={self.db_column_name!r}, name={self.name!r})"
        )

    def toCustomField(self) -> CustomField:
        field = msgspec.msgpack.decode(self.remote_data, type=CustomField)
        field.config = CustomFieldConfig(self.config)
        return field
    
    @classmethod
    def fromCustomField(cls, field: CustomField, existing: CustomFieldDb = None) -> CustomFieldDb:
        obj = existing if existing else cls()
        obj.db_column_name = field.db_column_name
        obj.name = field.name
        obj.remote_data = msgspec.msgpack.encode(field)
        obj.last_synced_at = datetime.now().timestamp()
        return obj
        
class PreferenceDb(Base):
    __tablename__ = "preference"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000))

    def __repr__(self) -> str:
        return f"Preference(key={self.key!r}, value={self.value!r})"

class BatteryDb(Base):
    __tablename__ = "battery"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_tag: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    location_id: Mapped[Optional[int]]
    remote_data: Mapped[Optional[bytes]]
    remote_modified_at: Mapped[Optional[str]] = mapped_column(String(50))
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(50))
    local_modified_at: Mapped[Optional[str]] = mapped_column(String(50))
    sync_status: Mapped[Optional[str]] = mapped_column(String(50))
    checked_out_to_asset_id: Mapped[Optional[str]] = mapped_column(String(100))
    checkout_pending_asset_id: Mapped[Optional[str]] = mapped_column(String(100))

    @classmethod
    def fromAsset(cls, asset: Asset, existing: BatteryDb = None) -> BatteryDb:
        obj = existing if existing else cls()
        obj.id = asset.id
        obj.asset_tag = asset.asset_tag
        obj.name = asset.name
        obj.location_id = asset.location.id if asset.location else None
        obj.remote_data = msgspec.msgpack.encode(asset)
        obj.remote_modified_at = datetime.strptime(
            asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S"
        ).timestamp()
        obj.last_synced_at = datetime.now().timestamp()
        assigned_asset_id = None
        if asset.assigned_to and getattr(asset.assigned_to, "type", None) == "asset":
            assigned_asset_id = str(asset.assigned_to.id)
        obj.checked_out_to_asset_id = assigned_asset_id
        if assigned_asset_id == obj.checkout_pending_asset_id:
            obj.checkout_pending_asset_id = None
        return obj

    def __repr__(self) -> str:
        return (
            f"Battery(id={self.id!r}, asset_tag={self.asset_tag!r}, name={self.name!r})"
        )


class StatusLabelDb(Base):
    __tablename__ = "status_label"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    type: Mapped[Optional[str]] = mapped_column(String(50))
    allowed: Mapped[Optional[bool]] = mapped_column(default=False)
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"StatusLabel(id={self.id!r}, name={self.name!r}, type={self.type!r})"

    @classmethod
    def fromStatusLabel(cls, label: StatusLabel, existing: StatusLabelDb = None) -> StatusLabelDb:
        obj = existing if existing else cls()
        obj.id = label.id
        obj.name = label.name
        obj.type = label.type
        obj.remote_data = msgspec.msgpack.encode(label)
        obj.last_synced_at = datetime.now().timestamp()
        return obj
    
    def toStatusLabelAsset(self) -> StatusLabelAsset:
        return StatusLabelAsset(
            id=self.id,
            name=self.name
        )

class FieldMappingDb(Base):
    __tablename__ = "field_mapping"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    db_column_name: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:
        return f"FieldMapping(id={self.id!r}, field_name={self.name!r}, db_column_name={self.db_column_name!r})"

class BatteryView(msgspec.Struct):
    id: int
    asset_tag: Optional[str]
    name: Optional[str]
    location: Optional[Location]
    status_label: Optional[StatusLabel]
    notes: Optional[str]
    purchased_date: Optional[str]
    custom_fields: Optional[dict[str, CustomFieldAsset]]
    checked_out_to_asset_id: Optional[str]
    checkout_pending_asset_id: Optional[str]

    remote_modified_at: Optional[str]
    last_synced_at: Optional[str]
    local_modified_at: Optional[str]
    sync_status: Optional[str]

    @classmethod
    def from_battery_db(cls, battery: BatteryDb) -> BatteryView:
        asset = (
            msgspec.msgpack.decode(battery.remote_data, type=Asset)
            if battery.remote_data
            else None
        )
        return cls(
            id=battery.id,
            asset_tag=battery.asset_tag,
            name=battery.name,
            location=asset.location if asset else None,
            status_label=asset.status_label if asset else None,
            notes=asset.notes if asset else None,
            remote_modified_at=battery.remote_modified_at,
            last_synced_at=battery.last_synced_at,
            local_modified_at=battery.local_modified_at,
            sync_status=battery.sync_status,
            custom_fields=asset.custom_fields if asset else None,
            purchased_date=asset.purchased_date if asset else None,
            checked_out_to_asset_id=battery.checked_out_to_asset_id,
            checkout_pending_asset_id=battery.checkout_pending_asset_id,
        )


class BatteryHistoryDb(Base):
    __tablename__ = "battery_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    battery_id: Mapped[int] = mapped_column(ForeignKey("battery.id"))
    asset_tag: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status_name: Mapped[Optional[str]] = mapped_column(String(255))
    location_name: Mapped[Optional[str]] = mapped_column(String(255))
    checkout_asset_id: Mapped[Optional[str]] = mapped_column(String(100))
    recorded_at: Mapped[Optional[str]] = mapped_column(String(50))
    custom_fields_blob: Mapped[Optional[bytes]]

    def custom_field_values(self) -> dict[str, Optional[str]]:
        if not self.custom_fields_blob:
            return {}
        return msgspec.msgpack.decode(
            self.custom_fields_blob, type=dict[str, Optional[str]]
        )

    @classmethod
    def from_asset(
        cls, asset: Asset, recorded_at: Optional[float] = None
    ) -> "BatteryHistoryDb":
        custom_values: dict[str, Optional[str]] = {}
        if asset.custom_fields:
            for field_asset in asset.custom_fields.values():
                if field_asset and field_asset.field:
                    custom_values[field_asset.field] = field_asset.value
        return cls(
            battery_id=asset.id,
            asset_tag=asset.asset_tag,
            name=asset.name,
            notes=asset.notes,
            status_name=asset.status_label.name if asset.status_label else None,
            location_name=asset.location.name if asset.location else None,
            checkout_asset_id=(
                str(asset.assigned_to.id)
                if asset.assigned_to and getattr(asset.assigned_to, "type", None) == "asset"
                else None
            ),
            recorded_at=str(recorded_at or datetime.now().timestamp()),
            custom_fields_blob=msgspec.msgpack.encode(custom_values),
        )


class KVStoreDb(Base):
    __tablename__ = "kv_store"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String(1000))

    def __repr__(self) -> str:
        return f"KVS(key={self.key!r}, value={self.value!r})"


class EventDb(Base):
    __tablename__ = "tba_event"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    start_date: Mapped[Optional[str]] = mapped_column(String(20))
    end_date: Mapped[Optional[str]] = mapped_column(String(20))
    year: Mapped[Optional[int]]
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state_prov: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"Event(key={self.key!r}, name={self.name!r})"

    @classmethod
    def from_tba_event(cls, event_data: dict, existing: 'EventDb' = None) -> 'EventDb':
        obj = existing if existing else cls()
        obj.key = event_data.get('key', '')
        obj.name = event_data.get('name')
        obj.start_date = event_data.get('start_date')
        obj.end_date = event_data.get('end_date')
        obj.year = event_data.get('year')
        obj.city = event_data.get('city')
        obj.state_prov = event_data.get('state_prov')
        obj.country = event_data.get('country')
        return obj


class MatchDb(Base):
    __tablename__ = "tba_match"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_key: Mapped[str] = mapped_column(String(50))
    comp_level: Mapped[str] = mapped_column(String(20))
    match_number: Mapped[int]
    set_number: Mapped[int]
    predicted_time: Mapped[Optional[int]]
    actual_time: Mapped[Optional[int]]
    red_alliance: Mapped[Optional[str]] = mapped_column(String(500))  # JSON list of team keys
    blue_alliance: Mapped[Optional[str]] = mapped_column(String(500))  # JSON list of team keys
    winning_alliance: Mapped[Optional[str]] = mapped_column(String(10))
    assigned_battery_id: Mapped[Optional[int]] = mapped_column(ForeignKey("battery.id"), nullable=True)
    last_synced_at: Mapped[Optional[str]] = mapped_column(String(50))

    def __repr__(self) -> str:
        return f"Match(key={self.key!r}, match_number={self.match_number!r})"

    @classmethod
    def from_tba_match(cls, match_data: dict, existing: 'MatchDb' = None) -> 'MatchDb':
        import json
        obj = existing if existing else cls()
        obj.key = match_data.get('key', '')
        obj.event_key = match_data.get('event_key', '')
        obj.comp_level = match_data.get('comp_level', '')
        obj.match_number = match_data.get('match_number', 0)
        obj.set_number = match_data.get('set_number', 1)
        obj.predicted_time = match_data.get('predicted_time')
        obj.actual_time = match_data.get('actual_time')
        obj.winning_alliance = match_data.get('winning_alliance')
        alliances = match_data.get('alliances') or {}
        obj.red_alliance = json.dumps((alliances.get('red') or {}).get('team_keys', []))
        obj.blue_alliance = json.dumps((alliances.get('blue') or {}).get('team_keys', []))
        obj.last_synced_at = str(datetime.now().timestamp())
        return obj

    def update_from_tba(self, match_data: dict):
        """Update match from TBA without changing battery assignment."""
        import json
        self.comp_level = match_data.get('comp_level', self.comp_level)
        self.match_number = match_data.get('match_number', self.match_number)
        self.set_number = match_data.get('set_number', self.set_number)
        self.predicted_time = match_data.get('predicted_time', self.predicted_time)
        self.actual_time = match_data.get('actual_time', self.actual_time)
        self.winning_alliance = match_data.get('winning_alliance', self.winning_alliance)
        alliances = match_data.get('alliances') or {}
        self.red_alliance = json.dumps((alliances.get('red') or {}).get('team_keys', []))
        self.blue_alliance = json.dumps((alliances.get('blue') or {}).get('team_keys', []))
        self.last_synced_at = str(datetime.now().timestamp())

    def to_dict(self) -> dict:
        import json
        return {
            'key': self.key,
            'event_key': self.event_key,
            'comp_level': self.comp_level,
            'match_number': self.match_number,
            'set_number': self.set_number,
            'predicted_time': self.predicted_time,
            'actual_time': self.actual_time,
            'red_alliance': json.loads(self.red_alliance) if self.red_alliance else [],
            'blue_alliance': json.loads(self.blue_alliance) if self.blue_alliance else [],
            'winning_alliance': self.winning_alliance,
            'assigned_battery_id': self.assigned_battery_id,
            'assigned_battery': None,  # populated by caller
            'last_synced_at': self.last_synced_at,
        }


class MatchBatteryAssignmentDb(Base):
    __tablename__ = "tba_match_battery_assignment"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_key: Mapped[str] = mapped_column(ForeignKey("tba_match.key"), nullable=False)
    battery_id: Mapped[int] = mapped_column(ForeignKey("battery.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[Optional[str]] = mapped_column(String(50))


def ensure_tba_match_battery_assignment_table(engine):
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "tba_match_battery_assignment" in existing_tables:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS tba_match_battery_assignment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_key TEXT NOT NULL,
                    battery_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY(match_key) REFERENCES tba_match(key),
                    FOREIGN KEY(battery_id) REFERENCES battery(id)
                )
                """
            )
        )


def ensure_battery_checkout_columns(engine):
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("battery")}
    statements = []
    if "checked_out_to_asset_id" not in existing_columns:
        statements.append(
            text("ALTER TABLE battery ADD COLUMN checked_out_to_asset_id TEXT")
        )
    if "checkout_pending_asset_id" not in existing_columns:
        statements.append(
            text("ALTER TABLE battery ADD COLUMN checkout_pending_asset_id TEXT")
        )
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(statement)


def ensure_battery_history_columns(engine):
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("battery_history")}
    statements = []
    if "status_name" not in existing_columns:
        statements.append(text("ALTER TABLE battery_history ADD COLUMN status_name TEXT"))
    if "location_name" not in existing_columns:
        statements.append(text("ALTER TABLE battery_history ADD COLUMN location_name TEXT"))
    if "checkout_asset_id" not in existing_columns:
        statements.append(text("ALTER TABLE battery_history ADD COLUMN checkout_asset_id TEXT"))
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(statement)


def ensure_user_role_column(engine):
    inspector = inspect(engine)
    existing_columns = {col["name"] for col in inspector.get_columns("user")}
    if "role" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'viewer'"))


def record_battery_history(
    session, battery: BatteryDb, recorded_at: Optional[float] = None
):
    """Persist a snapshot entry for the provided battery if it differs from the latest."""

    if not battery.remote_data:
        return None

    asset = msgspec.msgpack.decode(battery.remote_data, type=Asset)
    entry = BatteryHistoryDb.from_asset(asset, recorded_at)

    last_entry = (
        session.query(BatteryHistoryDb)
        .filter(BatteryHistoryDb.battery_id == entry.battery_id)
        .order_by(BatteryHistoryDb.recorded_at.desc())
        .first()
    )

    if (
        last_entry
        and last_entry.asset_tag == entry.asset_tag
        and (last_entry.name or "") == (entry.name or "")
        and (last_entry.notes or "") == (entry.notes or "")
        and (last_entry.status_name or "") == (entry.status_name or "")
        and (last_entry.location_name or "") == (entry.location_name or "")
        and (last_entry.checkout_asset_id or "") == (entry.checkout_asset_id or "")
        and (last_entry.custom_fields_blob or b"")
        == (entry.custom_fields_blob or b"")
    ):
        return last_entry

    session.add(entry)
    return entry