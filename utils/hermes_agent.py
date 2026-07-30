"""Bounded adapter for the locally installed Hermes Agent CLI."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass

from utils.config import config


@dataclass(frozen=True)
class HermesStatus:
    enabled: bool
    available: bool
    command: str
    safe_mode: bool
    timeout_seconds: int
    model: str
    provider: str
    toolsets: str

    def to_dict(self) -> dict:
        return asdict(self)


def hermes_status() -> HermesStatus:
    return HermesStatus(
        enabled=config.hermes_enabled,
        available=shutil.which(config.hermes_command) is not None,
        command=config.hermes_command,
        safe_mode=config.hermes_safe_mode,
        timeout_seconds=config.hermes_timeout_seconds,
        model=config.hermes_model,
        provider=config.hermes_provider,
        toolsets=config.hermes_toolsets,
    )


def run_hermes(prompt: str) -> str:
    """Run a single Hermes delegation with no shell and a bounded environment."""
    status = hermes_status()
    if not status.enabled:
        return (
            "Hermes delegation is disabled. Set HERMES_ENABLED=true and make "
            "HERMES_COMMAND available to the application container."
        )
    if not status.available:
        return f"Hermes command is not available: {status.command}"
    clean_prompt = (prompt or "").strip()[:12_000]
    if not clean_prompt:
        return "Hermes needs a non-empty task."

    args = [status.command]
    if status.safe_mode:
        args.append("--safe-mode")
    else:
        # Never inject repository rules into a delegated end-user task.
        args.append("--ignore-rules")
    if status.model:
        args.extend(["--model", status.model])
    if status.provider:
        args.extend(["--provider", status.provider])
    if status.toolsets:
        args.extend(["--toolsets", status.toolsets])
    args.extend(["--oneshot", clean_prompt])

    allowed_env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG", "LC_ALL", "TERM", "NO_COLOR"}
        or key.startswith("HERMES_")
    }
    allowed_env["NO_COLOR"] = "1"
    try:
        with tempfile.TemporaryDirectory(prefix="liquidround-hermes-") as workdir:
            result = subprocess.run(
                args,
                cwd=workdir,
                env=allowed_env,
                capture_output=True,
                text=True,
                timeout=status.timeout_seconds,
                check=False,
            )
    except subprocess.TimeoutExpired:
        return f"Hermes timed out after {status.timeout_seconds} seconds."
    except OSError as exc:
        return f"Hermes could not start: {exc}"

    output = (result.stdout or "").strip()
    if result.returncode != 0:
        detail = (result.stderr or output or "unknown Hermes error").strip()
        return f"Hermes delegation failed: {detail[:800]}"
    return output[:20_000] or "Hermes returned an empty response."
