# outaged

Parse structured outage logs, summarize them, and export to table or JSON.

## About

`outaged` is a minimal CLI tool for teams that maintain a simple text-based outage log. Each line records one outage as:

    service_name status_code started_at_ISO ended_at_ISO

It computes durations, summarizes statistics, filters by service or duration, and outputs either a formatted table or machine-readable JSON.

## Features

- Parse structured outage logs into typed records.
- Validate and reject malformed lines with clear errors.
- Filter by service name, minimum duration, or start time.
- Summarize total outages, affected services, total and average duration.
- Emit aligned table output or JSON.
- Small stdlib-only implementation with no external dependencies.

## Installation

```bash
python -m pip install -e .
```

## Usage

Sample log file `outages.log`:

    payments 503 2025-01-01T12:00:00Z 2025-01-01T12:02:00Z
    inventory 500 2025-01-02T01:30:00Z 2025-01-02T02:10:00Z
    payments 200 2025-01-03T08:00:00Z 2025-01-03T08:00:30Z

Run the CLI:

```bash
outaged -f outages.log
outaged -f outages.log --json
outaged -f outages.log --service payments --min-duration 60
outaged -f outages.log --since 2025-01-02T00:00:00Z
```

## Project structure

```
.
├── outaged/
│   ├── __init__.py
│   └── cli.py
├── tests/
│   └── test_outaged.py
├── pyproject.toml
└── README.md
```

## Tags / keywords

outage-log, log-parser, cli, python, json, monitoring
