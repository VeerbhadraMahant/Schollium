"""The single `scholium` entry point.

One subcommand per tool plus doctor. argparse with subparsers, no CLI framework,
per plan section 5.4. Tool subcommands are registered as they are built; until
then they are absent rather than stubbed, so `scholium --help` always tells the
truth about what exists.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from scholium import __version__, doctor
from scholium.config import Config, load

STATUS_MARK = {doctor.OK: "ok  ", doctor.WARN: "warn", doctor.FAIL: "FAIL"}


def _print_checks(checks: Sequence[doctor.Check], stream=None) -> int:
    # `stream` defaults to None, not sys.stdout, and is resolved here at call
    # time. A default bound at def-time would capture the *original* stdout
    # object, which escapes test runners (capsys, etc.) that swap sys.stdout
    # per test.
    if stream is None:
        stream = sys.stdout
    width = max((len(c.name) for c in checks), default=0)
    for check in checks:
        mark = STATUS_MARK.get(check.status, check.status)
        print(f"  [{mark}] {check.name.ljust(width)}  {check.detail}", file=stream)
    failed = [c for c in checks if c.status == doctor.FAIL and c.required]
    warned = [c for c in checks if c.status == doctor.WARN]
    print(file=stream)
    if failed:
        print(f"{len(failed)} required check(s) failed.", file=stream)
    else:
        print("All required checks passed.", file=stream)
    if warned:
        print(f"{len(warned)} warning(s).", file=stream)
    return 1 if failed else 0


def cmd_doctor(args: argparse.Namespace, config: Config) -> int:
    print(f"scholium {__version__}\n")
    return _print_checks(doctor.run(config))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scholium",
        description="A modular, local-first research assistant.",
    )
    parser.add_argument("--version", action="version", version=f"scholium {__version__}")
    parser.add_argument(
        "--root",
        metavar="DIR",
        help="repository root holding config.toml (default: search upwards from cwd)",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")
    doctor_parser = sub.add_parser(
        "doctor", help="report which services, models and clients are reachable"
    )
    doctor_parser.set_defaults(func=cmd_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1

    from pathlib import Path

    config = load(Path(args.root) if args.root else None)
    return args.func(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
