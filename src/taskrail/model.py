"""In-memory model of a project's backlogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from taskrail.config import BacklogConfig, Config


class Status(str, Enum):
    PENDING = "⬜"
    DONE = "✅"
    DISCARDED = "❌"

    @property
    def label(self) -> str:
        return self.name.lower()


NONE_MARKERS = {"", "—", "-"}


@dataclass
class Task:
    id: str
    status: Status | None
    status_raw: str
    kind: str
    points: int | None
    points_raw: str
    depends_on: list[str]
    title: str
    description: str
    columns: dict[str, str]
    backlog: str
    epic: str
    file: str
    line: int
    order: int


@dataclass
class Epic:
    id: str
    name: str
    objective: str
    file: str | None  # None when the epic section is inline in the backlog's main file
    backlog: str
    listing_line: int
    section_file: str | None = None
    section_line: int | None = None
    done_when: str | None = None
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Backlog:
    config: BacklogConfig
    epics: list[Epic] = field(default_factory=list)

    @property
    def tasks(self) -> list[Task]:
        return [task for epic in self.epics for task in epic.tasks]


@dataclass
class Project:
    config: Config
    backlogs: list[Backlog]
    kinds: dict  # name -> Kind; typed loosely to avoid an import cycle

    @property
    def tasks(self) -> list[Task]:
        return [task for backlog in self.backlogs for task in backlog.tasks]

    def task(self, task_id: str) -> Task | None:
        return next((task for task in self.tasks if task.id == task_id), None)

    def backlog_for_id(self, task_id: str) -> Backlog | None:
        for backlog in self.backlogs:
            prefix = backlog.config.prefix
            if task_id.startswith(prefix) and task_id[len(prefix):].isdigit():
                return backlog
        return None
