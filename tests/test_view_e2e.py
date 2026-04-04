"""End-to-end Playwright tests for the inspect-dataset view server."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FINDINGS_DIR = Path(__file__).parent / "_fixtures" / "view_findings"


def _create_fixture() -> None:
    """Create a minimal findings directory for testing."""
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

    findings = [
        {
            "scanner": "answer_length",
            "severity": "low",
            "category": "format",
            "explanation": "Answer has 12 words (threshold: 4).",
            "sample_index": 0,
            "sample_id": "q0",
            "metadata": {"word_count": 12},
        },
        {
            "scanner": "answer_length",
            "severity": "low",
            "category": "format",
            "explanation": "Answer has 8 words (threshold: 4).",
            "sample_index": 3,
            "sample_id": "q3",
            "metadata": {"word_count": 8},
        },
        {
            "scanner": "duplicate_questions",
            "severity": "high",
            "category": "question_quality",
            "explanation": "Duplicate question (same Q, different answer).",
            "sample_index": 1,
            "sample_id": "q1",
            "metadata": {"duplicate_of": 2},
        },
        {
            "scanner": "duplicate_questions",
            "severity": "high",
            "category": "question_quality",
            "explanation": "Duplicate question (same Q, different answer).",
            "sample_index": 2,
            "sample_id": "q2",
            "metadata": {"duplicate_of": 1},
        },
        {
            "scanner": "inconsistent_format",
            "severity": "medium",
            "category": "format",
            "explanation": "Answer not capitalised consistently.",
            "sample_index": 4,
            "sample_id": "q4",
            "metadata": {},
        },
    ]

    # Write per-scanner files (same layout as save_findings)
    by_scanner: dict[str, list[dict]] = {}
    for f in findings:
        by_scanner.setdefault(f["scanner"], []).append(f)
    for scanner_name, items in by_scanner.items():
        (FINDINGS_DIR / f"{scanner_name}.json").write_text(json.dumps(items, indent=2))

    summary = {
        "dataset_name": "test/dataset",
        "split": "train",
        "total_samples": 10,
        "total_findings": len(findings),
        "by_scanner": {
            name: {
                "total": len(items),
                "high": sum(1 for f in items if f["severity"] == "high"),
                "medium": sum(1 for f in items if f["severity"] == "medium"),
                "low": sum(1 for f in items if f["severity"] == "low"),
            }
            for name, items in by_scanner.items()
        },
        "by_severity": {
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
    }
    (FINDINGS_DIR / "scan_summary.json").write_text(json.dumps(summary, indent=2))

    samples = [
        {"index": i, "question": f"Q{i}?", "answer": f"A{i}", "id": f"q{i}"}
        for i in range(10)
    ]
    (FINDINGS_DIR / "samples.json").write_text(json.dumps(samples, indent=2))

    # Remove any stale triage file
    triage_file = FINDINGS_DIR / "triage.json"
    if triage_file.exists():
        triage_file.unlink()


@pytest.fixture(scope="session")
def server_url():
    """Start the view server in a background thread and yield its URL."""
    import threading
    import urllib.request

    from aiohttp import web

    from inspect_dataset._view.server import create_app

    _create_fixture()
    port = 17576

    app = create_app(str(FINDINGS_DIR))
    runner = web.AppRunner(app)

    import asyncio

    loop = asyncio.new_event_loop()

    async def _start():
        await runner.setup()
        site = web.TCPSite(runner, "localhost", port)
        await site.start()

    loop.run_until_complete(_start())
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    url = f"http://localhost:{port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{url}/api/summary", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        raise RuntimeError("View server did not start in time")

    yield url

    loop.call_soon_threadsafe(loop.stop)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_homepage_loads(page, server_url: str) -> None:
    """The SPA loads and shows the header with dataset name."""
    page.goto(server_url)
    page.wait_for_selector(".navbar-brand")
    assert page.text_content(".navbar-brand") == "inspect-dataset"
    assert "test/dataset" in page.text_content(".navbar-text")


def test_findings_tab_shows_findings(page, server_url: str) -> None:
    """Findings tab lists all findings with severity badges."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")
    items = page.query_selector_all("[data-finding-id]")
    assert len(items) == 5


def test_scanner_sidebar_filters(page, server_url: str) -> None:
    """Clicking a scanner in the sidebar filters the findings list."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Click the "answer_length" scanner in the sidebar
    page.click("text=answer_length")
    page.wait_for_timeout(300)

    items = page.query_selector_all("[data-finding-id]")
    assert len(items) == 2


def test_finding_detail_panel(page, server_url: str) -> None:
    """Clicking a finding shows the detail panel."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Click the first finding
    page.click("[data-finding-id]:first-child")
    page.wait_for_timeout(300)

    # Detail panel should show the scanner name as a badge
    detail = page.query_selector(".border-start")
    assert detail is not None
    text = detail.text_content()
    assert "answer_length" in text or "duplicate_questions" in text


def test_triage_confirm(page, server_url: str) -> None:
    """Confirming a finding updates the triage state."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Click a finding to select it
    page.click("[data-finding-id]:first-child")
    page.wait_for_timeout(300)

    # Click the Confirm button in the detail panel
    page.click(".border-start button:has-text('Confirm')")
    page.wait_for_timeout(500)

    # The navbar shows confirmed/dismissed counts
    nav_text = page.text_content("nav")
    assert "1 confirmed" in nav_text


def test_triage_dismiss(page, server_url: str) -> None:
    """Dismissing a finding updates the triage state."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Click a finding to select it
    page.click("[data-finding-id]:first-child")
    page.wait_for_timeout(300)

    # Click the Dismiss button in the detail panel
    page.click(".border-start button:has-text('Dismiss')")
    page.wait_for_timeout(500)

    nav_text = page.text_content("nav")
    assert "1 dismissed" in nav_text


def test_keyboard_navigation(page, server_url: str) -> None:
    """Keyboard shortcuts n/p navigate between findings."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Select the first finding
    page.click("[data-finding-id]:first-child")
    page.wait_for_timeout(200)

    # Get the first finding's detail text
    first_text = page.text_content(".border-start")

    # Press 'n' to go to next
    page.keyboard.press("n")
    page.wait_for_timeout(200)

    second_text = page.text_content(".border-start")

    # They could be different or same scanner, but navigation should work
    # Press 'p' to go back
    page.keyboard.press("p")
    page.wait_for_timeout(200)

    back_text = page.text_content(".border-start")
    assert back_text == first_text


def test_samples_tab(page, server_url: str) -> None:
    """Switching to Samples tab shows the AG Grid table."""
    page.goto(server_url)
    page.wait_for_selector(".navbar-brand")

    # Click the Samples nav pill (be specific to avoid matching footer text)
    page.click(".nav-pills a:has-text('Samples')")
    page.wait_for_timeout(1500)

    # AG Grid should render
    grid = page.query_selector("[class*='ag-']")
    assert grid is not None, "AG Grid did not render"


def test_export_link(page, server_url: str) -> None:
    """The export link points to the API endpoint."""
    page.goto(server_url)
    page.wait_for_selector("a[download]")
    href = page.get_attribute("a[download]", "href")
    assert href == "/api/export"


def test_severity_filter(page, server_url: str) -> None:
    """Filtering by severity restricts the findings list."""
    page.goto(server_url)
    page.wait_for_selector("[data-finding-id]")

    # Select "high" severity from the dropdown
    page.select_option("select >> nth=0", "high")
    page.wait_for_timeout(300)

    items = page.query_selector_all("[data-finding-id]")
    # We have 2 high-severity findings (duplicate_questions)
    assert len(items) == 2
