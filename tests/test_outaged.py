from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from outaged import OutagedError, OutageRecord, filter_records, format_json, format_table, load_records, main, summarize


def load_records_from_text(text: str) -> "List[OutageRecord]":
    import tempfile

    handle = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False, encoding="utf-8")
    try:
        handle.write(text)
        handle.flush()
        handle.close()
        return load_records(handle.name)
    finally:
        os.unlink(handle.name)


VALID_LOG = "\n".join(
    [
        "payments 503 2025-01-01T12:00:00Z 2025-01-01T12:02:00Z",
        "inventory 500 2025-01-02T01:30:00Z 2025-01-02T02:10:00Z",
        "payments 200 2025-01-03T08:00:00Z 2025-01-03T08:00:30Z",
    ]
)


def test_outage_record_from_line_positive() -> None:
    record = OutageRecord.from_line(VALID_LOG.splitlines()[0])
    assert record.service == "payments"
    assert record.status_code == "503"
    assert record.duration_seconds == 120


def test_outage_record_from_line_negative() -> None:
    with pytest.raises(OutagedError):
        OutageRecord.from_line("this is not valid")


def test_outage_record_duration_edge_case() -> None:
    record = OutageRecord.from_line("x 500 2025-01-01T00:00:00Z 2025-01-01T00:00:00Z")
    assert record.duration_seconds == 0


def test_load_records_positive(tmp_path: "pytest.TempPathFactory") -> None:
    path = tmp_path / "outages.log"
    path.write_text(VALID_LOG, encoding="utf-8")
    records = load_records(str(path))
    assert len(records) == 3
    assert [record.service for record in records] == ["payments", "inventory", "payments"]


def test_load_records_ignores_blank_and_comments(tmp_path: "pytest.TempPathFactory") -> None:
    path = tmp_path / "outages.log"
    path.write_text(
        "\n".join(["# header", "", "payments 503 2025-01-01T12:00:00Z 2025-01-01T12:02:00Z", "   ", "# trailing"]),
        encoding="utf-8",
    )
    records = load_records(str(path))
    assert len(records) == 1
    assert records[0].service == "payments"


def test_filter_records_by_service() -> None:
    records = load_records_from_text(VALID_LOG)
    filtered = filter_records(records, service="payments")
    assert all(record.service == "payments" for record in filtered)
    assert len(filtered) == 2


def test_filter_records_by_min_duration() -> None:
    records = load_records_from_text(VALID_LOG)
    filtered = filter_records(records, min_duration=180)
    assert all(record.duration_seconds >= 180 for record in filtered)
    assert [record.service for record in filtered] == ["inventory"]


def test_filter_records_by_since() -> None:
    records = load_records_from_text(VALID_LOG)
    filtered = filter_records(records, since="2025-01-02T00:00:00Z")
    assert all(record.started_at >= "2025-01-02T00:00:00Z" for record in filtered)
    assert [record.service for record in filtered] == ["inventory", "payments"]


def test_summarize_computes_expected_values() -> None:
    records = load_records_from_text(VALID_LOG)
    summary = summarize(records)
    assert summary["total_outages"] == 3
    assert summary["service_count"] == 2
    assert summary["services_affected"] == ["inventory", "payments"]
    assert summary["total_duration_seconds"] == 120 + 2400 + 30
    assert summary["avg_duration_seconds"] == (120 + 2400 + 30) // 3


def test_format_table_positive() -> None:
    records = load_records_from_text(VALID_LOG)
    text = format_table(records)
    assert "Service" in text
    assert "payments" in text
    assert "inventory" in text


def test_format_table_negative() -> None:
    assert format_table([]) == "No matching outage records.\n"


def test_format_json_positive() -> None:
    records = load_records_from_text(VALID_LOG)
    text = format_json(records)
    parsed = json.loads(text)
    assert len(parsed) == 3
    assert parsed[0]["service"] == "payments"


def test_format_json_edge_case_empty() -> None:
    assert format_json([]) == "[]\n"


def test_main_positive_table(tmp_path: "pytest.TempPathFactory") -> None:
    path = tmp_path / "outages.log"
    path.write_text(VALID_LOG, encoding="utf-8")
    rc = main(["-f", str(path)])
    assert rc == 0


def test_main_positive_json(tmp_path: "pytest.TempPathFactory") -> None:
    path = tmp_path / "outages.log"
    path.write_text(VALID_LOG, encoding="utf-8")
    rc = main(["-f", str(path), "--json"])
    assert rc == 0


def test_main_negative_missing_file() -> None:
    rc = main(["-f", "/nonexistent/path/outages.log"])
    assert rc == 1


def test_main_edge_case_invalid_line(tmp_path: "pytest.TempPathFactory") -> None:
    path = tmp_path / "outages.log"
    path.write_text("not a valid line\n", encoding="utf-8")
    rc = main(["-f", str(path)])
    assert rc == 1


def test_main_help_succeeds() -> None:
    rc = main(["--help"])
    assert rc == 0


def test_main_version_succeeds() -> None:
    rc = main(["--version"])
    assert rc == 0
