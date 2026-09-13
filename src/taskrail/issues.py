"""Validation issues and error types shared across modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    file: str | None = None
    line: int | None = None

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "file": self.file,
            "line": self.line,
        }

    def format(self) -> str:
        where = ""
        if self.file:
            where = f"{self.file}:{self.line}: " if self.line else f"{self.file}: "
        return f"{where}{self.severity}: {self.message} [{self.code}]"


def error(code: str, message: str, file: str | None = None, line: int | None = None) -> Issue:
    return Issue("error", code, message, file, line)


def warning(code: str, message: str, file: str | None = None, line: int | None = None) -> Issue:
    return Issue("warning", code, message, file, line)


class ConfigError(Exception):
    """The project configuration cannot be loaded at all."""
