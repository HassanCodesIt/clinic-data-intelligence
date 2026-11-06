from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Practice(BaseModel):
    id: int
    name: str
    address: str = ""
    suburb: str = ""
    state: str = ""
    postcode: str = ""
    phone: str = ""
    website: str = ""
    lat: float | None = None
    lon: float | None = None
    fields: dict[str, object] = {}


class PracticePage(BaseModel):
    items: list[Practice]
    page: int
    page_size: int
    total: int
    without_coordinates: int = 0


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class PracticeFilter(BaseModel):
    model_config = {"extra": "forbid"}
    state: str | None = None
    postcode: str | None = None
    q: str | None = None

    @field_validator("state")
    @classmethod
    def normalise_state(cls, value: str | None) -> str | None:
        if not value:
            return value
        return "Unknown" if value.strip().lower() == "unknown" else value.upper()


class AskResponse(BaseModel):
    filter: PracticeFilter
    results: PracticePage


class EnrichRequest(BaseModel):
    website: HttpUrl


class WebsiteCandidate(BaseModel):
    id: int | None = None
    url: str
    title: str = ""
    snippet: str = ""
    confidence: float = Field(ge=0, le=1)
    reason: str = ""


class Enrichment(BaseModel):
    email: str = ""
    phone: str = ""
    services: list[str] = []
    bulk_billing: str = ""
    languages: list[str] = []
    hours: str = ""
    confidence: dict[str, float] = {}
    source_snippets: dict[str, str] = {}


class OutreachDraft(BaseModel):
    subject: str
    body: str
    ai_generated: Literal[True] = True
