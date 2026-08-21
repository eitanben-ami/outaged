"""
outaged
=======

Parse structured outage logs and summarize them.

Example log lines::

    payments 503 2025-01-01T12:00:00Z 2025-01-01T12:02:00Z
    inventory 500 2025-01-02T01:30:00Z 2025-01-02T02:10:00Z
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence


__version__ = "0.1.0"

LOG_LINE_RE = re.compile(
    r"^(?P<service>\S+)\s+(?P<status>\d{3})\s+(?P<started>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(?P<ended>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$"
)

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class OutagedError(Exception):
    """Base CLI error."""


@dataclass(frozen=True)
class OutageRecord:
    service: str
    status_code: str
    started_at: str
    ended_at: str
    duration_seconds: int

    @staticmethod
    def from_line(line: str) -> "OutageRecord":
        match = LOG_LINE_RE.match(line.strip())
        if not match:
            raise OutagedError(f"Invalid outage line: {line.strip()!r}")
        started = datetime.strptime(match.group("started"), ISO_FORMAT)
        ended = datetime.strptime(match.group("ended"), ISO_FORMAT)
        duration = int((ended - started).total_seconds())
        return OutageRecord(
            service=match.group("service"),
            status_code=match.group("status"),
            started_at=match.group("started"),
            ended_at=match.group("ended"),
            duration_seconds=duration,
        )


def load_records(path: str) -> List[OutageRecord]:
    records: List[OutageRecord] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            records.append(OutageRecord.from_line(line))
    return records


def filter_records(
    records: Sequence[OutageRecord],
    service: Optional[str] = None,
    min_duration: Optional[int] = None,
    since: Optional[str] = None,
) -> List[OutageRecord]:
    out: List[OutageRecord] = []
    for record in records:
        if service is not None and record.service != service:
            continue
        if min_duration is not None and record.duration_seconds < min_duration:
            continue
        if since is not None and record.started_at < since:
            continue
        out.append(record)
    return out


def summarize(records: Iterable[OutageRecord]) -> dict:
    seq = list(records)
    total = len(seq)
    services: List[str] = sorted({record.service for record in seq})
    total_duration = sum(record.duration_seconds for record in seq)
    avg_duration = (total_duration // total) if total else 0
    return {
        "total_outages": total,
        "services_affected": services,
        "service_count": len(services),
        "total_duration_seconds": total_duration,
        "avg_duration_seconds": avg_duration,
    }


def format_table(records: Sequence[OutageRecord], width: int = 120) -> str:
    if not records:
        return "No matching outage records.\n"
    header = f"{'Service':<20} {'Status':<8} {'Started':<26} {'Ended':<26} {'Duration':>12}\n"
    divider = "-" * 96 + "\n"
    lines = [header, divider]
    for record in records:
        lines.append(
            f"{record.service:<20} {record.status_code:<8} {record.started_at:<26} {record.ended_at:<26} {record.duration_seconds:>12}\n"
        )
    body = "".join(lines)
    return body


def format_json(records: Sequence[OutageRecord]) -> str:
    payload = [
        {
            "service": record.service,
            "status_code": record.status_code,
            "started_at": record.started_at,
            "ended_at": record.ended_at,
            "duration_seconds": record.duration_seconds,
        }
        for record in records
    ]
    return json.dumps(payload, indent=2) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="outaged",
        description="Parse structured outage logs and summarize them.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"outaged {__version__}",
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="Path to the outage log file.",
    )
    parser.add_argument(
        "--service",
        default=None,
        help="Filter to a single service name.",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=None,
        help="Minimum outage duration in seconds.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Include outages that started on or after this ISO timestamp, e.g. 2025-01-01T00:00:00Z.",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Emit JSON instead of a formatted table.",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=120,
        help="Table display width hint.",
    )
    parser.set_defaults(command="table")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code in (None, 0):
            return 0
        return int(exc.code)
    try:
        records = load_records(args.file)
    except FileNotFoundError as exc:
        print(f"outaged: {exc}", file=sys.stderr)
        return 1
    except OutagedError as exc:
        print(f"outaged: {exc}", file=sys.stderr)
        return 1

    filtered = filter_records(
        records,
        service=args.service,
        min_duration=args.min_duration,
        since=args.since,
    )

    if args.json:
        output = format_json(filtered)
    else:
        output = format_table(filtered, width=args.width)

    sys.stdout.write(output)
    return 0


__all__ = [
    "OutageRecord",
    "OutagedError",
    "filter_records",
    "format_json",
    "format_table",
    "load_records",
    "main",
    "summarize",
]
