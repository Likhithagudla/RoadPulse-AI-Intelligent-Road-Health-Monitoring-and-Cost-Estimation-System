"""
RoadPulse AI - Pagination Utilities
Provides safe pagination query parameters and metadata structures.
"""

from typing import Tuple
from fastapi import Query


def pagination_params(
    limit: int = Query(50, ge=1, le=1000, description="Items per page (max 1000)"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> Tuple[int, int]:
    """Dependency that returns (limit, offset) with bounds enforcement."""
    return limit, offset
