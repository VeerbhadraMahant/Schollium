"""Load a versioned prompt file. Prompts are never inlined in code (CLAUDE.md):
changing wording means a new `<name>.v<N>.txt` file, which shows up in every
run's config snapshot because the version number is part of the filename.
"""

from __future__ import annotations

from pathlib import Path


def load_prompt(name: str, version: int, *, prompts_dir: Path) -> str:
    """`name` is `<tool>.<step>`, for example `find.expand` or
    `rerank.pointwise`. Raises FileNotFoundError with the path it looked for,
    since a missing prompt should never fail silently into an empty string.
    """
    path = prompts_dir / f"{name}.v{version}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"no prompt file at {path}")
    return path.read_text(encoding="utf-8")
