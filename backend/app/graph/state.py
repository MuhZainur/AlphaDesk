import re
from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, field_validator
from typing_extensions import TypedDict

from app import config


class Step(BaseModel):
    id: int
    worker: Literal["technical", "fundamental", "news"]
    ticker: str
    goal: str

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, v: str) -> str:
        v = v.upper().strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", v):
            raise ValueError("bad ticker")
        return v


class Plan(BaseModel):
    steps: list[Step]

    @field_validator("steps")
    @classmethod
    def _cap(cls, v: list[Step]) -> list[Step]:
        return v[: config.MAX_STEPS]


class Finding(BaseModel):
    step_id: int
    worker: str
    ticker: str
    evidence: dict
    notes: str


class Critique(BaseModel):
    verdict: Literal["pass", "revise"]
    issues: list[str] = []


def add_or_reset(old: list, new):
    """Findings reducer: workers append in parallel, load_memory resets it at the start of each turn."""
    return [] if new == "reset" else (old or []) + new


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_id: str
    profile: dict
    summaries: list
    plan: list[Step]
    findings: Annotated[list, add_or_reset]
    draft: str
    critique: Critique | None
    revisions: int
    final: str
