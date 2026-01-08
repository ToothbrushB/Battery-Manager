from __future__ import annotations
from typing import Optional, Generic, TypeVar

from helpers import *
import msgspec

T = TypeVar('T')
class Paginated(msgspec.Struct, Generic[T]):
    """A generic paginated API wrapper, parametrized by the item type."""
    total: int       # The total number of items found
    rows: list[T]   # Items returned, up to `per_page` in length
    
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
    name: str
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
    
class Model(msgspec.Struct):
    id: int
    name: str
class StatusLabel(msgspec.Struct):
    id: int
    name: str
    status_type: str
    status_meta: str
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
    field: str
    value: Optional[str] = None
    field_format: Optional[str] = None
    element: Optional[str] = None
class Asset(msgspec.Struct):
    id: int
    name: str
    asset_tag: str
    status_label: StatusLabel
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
    custom_fields: Optional[dict[str, CustomField]] = None
    
    
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class Base(DeclarativeBase):
    pass

class LocationDb(Base):
    __tablename__ = "location"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]]
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("location.id"))
    last_synced_at: Mapped[Optional[str]]
    def __repr__(self) -> str:
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"


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
    def __repr__(self) -> str:
        return f"Battery(id={self.id!r}, asset_tag={self.asset_tag!r}, name={self.name!r})"

class BatteryView(msgspec.Struct):
    id: int
    asset_tag: Optional[str]
    name: Optional[str]
    location: Optional[Location]
    status_label: Optional[StatusLabel]
    notes: Optional[str]
    purchased_date: Optional[str]
    custom_fields: Optional[dict[str, CustomField]]
    
    remote_modified_at: Optional[str]
    last_synced_at: Optional[str]
    local_modified_at: Optional[str]
    sync_status: Optional[str]
    
    @classmethod
    def from_battery_db(cls, battery: BatteryDb) -> BatteryView:
        asset = msgspec.msgpack.decode(battery.remote_data, type=Asset) if battery.remote_data else None
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