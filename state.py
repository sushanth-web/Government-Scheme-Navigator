"""Shared LangGraph state for the Scheme Navigator project.

Every agent (intake, retriever, eligibility, document, verifier, action)
reads from and writes to the same GraphState object.
"""

from __future__ import annotations
from typing import Literal, Optional

from pydantic import BaseModel

Language = Literal["en", "te", "hi"]


class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    state: str = "Andhra Pradesh"
    district: Optional[str] = None
    occupation: Optional[str] = None  # farmer, student, laborer, ...
    annual_income: Optional[int] = None  # INR per year
    land_acres: Optional[float] = None
    caste_category: Optional[Literal["OC", "BC", "SC", "ST", "EWS", "Minority"]] = None


# Fields the intake agent must fill before the graph moves on.
REQUIRED_FIELDS = ["age","gender", "occupation", "district", "annual_income"]

