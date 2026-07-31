"""Registered, resource-bounded HermiT locality-module validation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HermitCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    module: str
    signature: list[str]
    maximum_module_axioms: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0, le=3600)
    maximum_memory_mb: int = Field(ge=128, le=32768)
    contradiction_fixture: str

    @field_validator("id", "module", "contradiction_fixture")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class HermitRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    checks: list[HermitCheck]

    @classmethod
    def load(cls, path: Path) -> "HermitRegistry":
        registry = cls.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        ids = [check.id for check in registry.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate HermiT check ids")
        return registry


def run_registered_checks(registry_path: Path, root: Path) -> list[dict[str, object]]:
    """Run every declared module and require its contradiction fixture to be rejected."""
    registry = HermitRegistry.load(registry_path)
    results: list[dict[str, object]] = []
    for check in registry.checks:
        module = (root / check.module).resolve()
        contradiction = (root / check.contradiction_fixture).resolve()
        for path in (module, contradiction):
            if not path.is_file():
                raise FileNotFoundError(path)
        command = ["gradle", "--quiet", "-p", str(root / "ontology"), "run",
                   f"--args=--hermit {module} {check.maximum_module_axioms}"]
        env = dict(os.environ)
        env["JAVA_TOOL_OPTIONS"] = f"-Xmx{check.maximum_memory_mb}m"
        completed = subprocess.run(command, cwd=root, env=env, timeout=check.timeout_seconds,
                                   text=True, capture_output=True)
        if completed.returncode:
            raise RuntimeError(f"HermiT check {check.id!r} failed:\n{completed.stdout}{completed.stderr}")
        contradiction_command = command[:-1] + [
            f"--args=--hermit {contradiction} {check.maximum_module_axioms}"
        ]
        rejected = subprocess.run(contradiction_command, cwd=root, env=env,
                                  timeout=check.timeout_seconds, text=True,
                                  capture_output=True)
        if rejected.returncode == 0:
            raise RuntimeError(f"HermiT contradiction fixture for {check.id!r} was accepted")
        results.append({"id": check.id, "status": "passed",
                        "maximum_module_axioms": check.maximum_module_axioms,
                        "timeout_seconds": check.timeout_seconds,
                        "maximum_memory_mb": check.maximum_memory_mb})
    return results
