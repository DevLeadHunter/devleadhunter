"""Where the professional license stored on a prospect enrichment came from."""

from enum import Enum


class ProfessionalLicenseSource(str, Enum):
    """Origin of ``professional_license_label`` / ``professional_license_number``.

    A human-typed number always wins: the registry lookup never overwrites a MANUAL value.
    """

    MANUAL = "manual"
    RBQ_REGISTRY = "rbq_registry"
