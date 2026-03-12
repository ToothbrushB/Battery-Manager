from __future__ import annotations
from datetime import datetime
import enum
from typing import Optional, Generic, TypeVar
import msgspec
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
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


class Company(msgspec.Struct):
    id: int
    name: str
    tag_color: Optional[str] = None


class Assignee(msgspec.Struct):
    id: int
    name: str
    type: str


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
    username: Mapped[str] = mapped_column(primary_key=True)
    password: Mapped[str]

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, password={self.password!r})"
    
class LocationDb(Base):
    __tablename__ = "location"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]]
    allowed: Mapped[Optional[bool]] = mapped_column(default=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("location.id"))
    is_parent: Mapped[bool] = mapped_column(default=False)
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"

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
    db_column_name: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]]
    config: Mapped[CustomFieldConfig] = mapped_column(
        String, default=CustomFieldConfig.HIDE.value
    )
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]]

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
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Preference(key={self.key!r}, value={self.value!r})"

class BatteryDb(Base):
    __tablename__ = "battery"
    id: Mapped[int] = mapped_column(primary_key=True)
    asset_tag: Mapped[Optional[str]]
    name: Mapped[Optional[str]]
    location_id: Mapped[Optional[int]]
    remote_data: Mapped[Optional[bytes]]
    remote_modified_at: Mapped[Optional[str]]
    last_synced_at: Mapped[Optional[str]]
    local_modified_at: Mapped[Optional[str]]
    sync_status: Mapped[Optional[str]]

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
        return obj

    def __repr__(self) -> str:
        return (
            f"Battery(id={self.id!r}, asset_tag={self.asset_tag!r}, name={self.name!r})"
        )


class StatusLabelDb(Base):
    __tablename__ = "status_label"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]]
    type: Mapped[Optional[str]]
    allowed: Mapped[Optional[bool]] = mapped_column(default=False)
    remote_data: Mapped[Optional[bytes]]
    last_synced_at: Mapped[Optional[str]]

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
    name: Mapped[str]
    db_column_name: Mapped[str]

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
        )


class KVStoreDb(Base):
    __tablename__ = "kv_store"
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"KVS(key={self.key!r}, value={self.value!r})"