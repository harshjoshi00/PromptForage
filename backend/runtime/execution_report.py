"""
Execution Report — models the result of runtime simulation.
"""

from __future__ import annotations
from pydantic import BaseModel, Field


class ExecutionCheck(BaseModel):
    """A single executability check result."""
    name: str
    passed: bool
    details: str = ""


class ExecutionReport(BaseModel):
    """Report from the runtime simulator."""
    is_executable: bool = True
    checks: list[ExecutionCheck] = Field(default_factory=list)
    generated_files: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    preview_html: str = ""  # Inline HTML preview of the generated app

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    def add_check(self, name: str, passed: bool, details: str = ""):
        check = ExecutionCheck(name=name, passed=passed, details=details)
        self.checks.append(check)
        if not passed:
            self.is_executable = False

    def to_dict(self) -> dict:
        return {
            "is_executable": self.is_executable,
            "checks_passed": self.pass_count,
            "checks_failed": self.fail_count,
            "checks": [c.model_dump() for c in self.checks],
            "generated_files": self.generated_files,
            "errors": self.errors,
        }
