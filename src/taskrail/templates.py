"""Rendering the path and branch templates of a kind for a concrete task."""

from __future__ import annotations

import re

from taskrail.config import Config
from taskrail.model import Task


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "untitled"


def render(template: str | None, task: Task, config: Config) -> str | None:
    if template is None:
        return None
    backlog = config.backlog(task.backlog)
    values = {
        "id": task.id,
        "slug": slugify(task.title),
        "artifacts": backlog.artifacts if backlog else "docs",
        "backlog": task.backlog,
        "epic": task.epic,
    }
    return template.format(**values)
