"""Discovery and validation for the local NASA FIRMS archive extracts."""

from fire_data.discover import discover_all
from fire_data.validate import validate_all

__all__ = ["discover_all", "validate_all"]
