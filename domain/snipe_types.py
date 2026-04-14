"""Domain types extracted from legacy models module.

Phase 2 keeps runtime compatibility by re-exporting current msgspec structs,
while giving callers a stable import path for domain objects.
"""

from models import (  # noqa: F401
    Paginated,
    DateTime,
    Date,
    Company,
    Department,
    User,
    Location,
    Model,
    StatusLabelAsset,
    Category,
    Manufacturer,
    Supplier,
    Depreciation,
    Assignee,
    CustomField,
    CustomFieldAsset,
    StatusLabel,
    Asset,
    BatteryView,
)
