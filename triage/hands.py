"Checks what the model asks for and only lets safe changes through."

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Rules(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed_actions: frozenset[str] = frozenset({"add_label"})
    labels: dict[str, str] = {
        "bug": "something is broken",
        "question": "someone is asking how to do something",
        "idea": "a suggestion or a new feature",
    }
    max_actions_per_run: int = 5


class Request(BaseModel):
    issue: int = Field(description="Number of the issue being triaged")
    action: str = Field(description="What to do. Only add_label is allowed")
    label: str | None = Field(default=None, description="One of the labels you were given")


class Outcome(StrEnum):
    DONE = "DONE"
    REFUSED = "REFUSED"
    ALREADY_DONE = "ALREADY DONE"
    SKIPPED = "SKIPPED"


def decide(
    request: Request, *, issue: int, labels: frozenset[str], done: int, rules: Rules
) -> tuple[Outcome, str]:
    """Anything not explicitly allowed is refused."""
    if request.issue != issue:
        return Outcome.REFUSED, "targets a different issue"
    if request.action not in rules.allowed_actions:
        return Outcome.REFUSED, f"action '{request.action}' not allowed"
    if request.label not in rules.labels:
        return Outcome.REFUSED, f"label '{request.label}' not allowed"
    if labels & rules.labels.keys():
        return Outcome.ALREADY_DONE, "already labelled"
    if done >= rules.max_actions_per_run:
        return Outcome.SKIPPED, "limit for this run reached"
    return Outcome.DONE, "allowed"
