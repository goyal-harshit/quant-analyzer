"""Pydantic schemas for the stocks module.

Endpoints currently return provider-shaped dicts (consumed directly by the
frontend), so these are light request/typing helpers rather than strict
response models, to preserve the existing API contract during the revamp.
"""

from typing import Optional
from pydantic import BaseModel


class Bollinger(BaseModel):
    upper: Optional[float] = None
    middle: Optional[float] = None
    lower: Optional[float] = None
