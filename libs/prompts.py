"""Every question the commands ask, so cancelling one always means the same no."""

import re
from collections.abc import Sequence
from typing import Any

import questionary

EMPTY = "(empty)"
NEW = "(new template)"
SKIP = "(skip export)"


def valid(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", name))


def select(question: str, choices: Sequence[Any]) -> Any | None:
    return questionary.select(question, choices=list(choices)).ask()


def confirm(question: str) -> bool:
    return bool(questionary.confirm(question, default=False).ask())


def source(existing: Sequence[str], extra: Sequence[str] = ()) -> str | None:
    return select("Template", [*extra, *existing])


def target(existing: Sequence[str]) -> str | None:
    choice = select("Template", [NEW, *existing])
    if choice is None or choice != NEW:
        return choice
    return questionary.text("Template name", validate=valid).ask()
