from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Competition = Literal["women", "men"]


class Match(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    competition: Competition
    phase: str = "Preliminary"
    round: str = ""
    match_no: str = ""
    starts_at_utc: datetime
    team_a: str
    team_b: str
    score: str | None = None
    venue: str = ""
    city: str = ""
    country: str = ""
    status: str = "scheduled"

    @field_validator("starts_at_utc")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            msg = "starts_at_utc must include a timezone"
            raise ValueError(msg)
        return value


class ScheduleData(BaseModel):
    version: str = "unknown"
    source_name: str = "Unknown source"
    source_url: str = ""
    generated_at: datetime | None = None
    matches: list[Match] = Field(default_factory=list)

    def competitions(self) -> list[Competition]:
        present = {match.competition for match in self.matches}
        return [competition for competition in ("women", "men") if competition in present]
