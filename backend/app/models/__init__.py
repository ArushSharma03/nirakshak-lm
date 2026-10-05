"""
Database models sub-package.

All models are imported here so that:
1. Alembic can discover them for auto-migration generation.
2. Application code can do `from app.models import User, Inspection, ...`
"""

from app.models.user import User, UserRole                        # noqa: F401
from app.models.product import Product, ProductCategory            # noqa: F401
from app.models.inspection import (                                # noqa: F401
    Inspection,
    InspectionStatus,
    ComplianceOutcome,
)
from app.models.package_image import (                             # noqa: F401
    PackageImage,
    ViewType,
    QualityStatus,
)
