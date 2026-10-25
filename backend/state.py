from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel

Language = Literal["en", "te", "hi"]


class UserProfile(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    state: str = "Andhra Pradesh"
    district: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[int] = None
    land_acres: Optional[float] = None
    caste_category: Optional[Literal["OC", "BC", "SC", "ST", "EWS", "Minority"]] = None

    # filled by intake_node (the language the user picked, for the voice agents)
    language: Optional[str] = None      # "English" / "Telugu" / "Hindi"
    locale: Optional[str] = None        # "en-IN" / "te-IN" / "hi-IN"

    # filled by eligibility_node
    ranked_schemes: Optional[str] = None
    selected_schemes: list[str] = []

    # filled by document_node
    scheme_details: list[dict] = []      # per scheme: documents, dates, steps
    document_checklist: list[dict] = []  # one combined list: document + needed_for


REQUIRED_FIELDS = ["age", "gender", "occupation", "district", "annual_income"]