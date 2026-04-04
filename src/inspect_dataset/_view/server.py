"""aiohttp backend for the interactive dataset explorer."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "www" / "dist"


class _WWWResource(web.StaticResource):
    """SPA-aware static resource (mirrors inspect_ai pattern).

    Serves /index.html for any path that doesn't match an existing
    static file, and disables caching so we never serve stale assets.
    """

    def __init__(self) -> None:
        super().__init__(
            "",
            os.path.abspath((Path(__file__).parent / "www" / "dist").as_posix()),
        )

    async def _handle(self, request: web.Request) -> web.StreamResponse:
        filename = request.match_info["filename"]
        if not filename:
            request.match_info["filename"] = "index.html"

        response = await super()._handle(request)

        # Disable caching — only served locally
        response.headers.update(
            {
                "Expires": "Fri, 01 Jan 1990 00:00:00 GMT",
                "Pragma": "no-cache",
                "Cache-Control": ("no-cache, no-store, max-age=0, must-revalidate"),
            }
        )
        return response


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def create_app(findings_dir: str | Path) -> web.Application:
    """Create the aiohttp application for serving the explorer UI."""
    findings_path = Path(findings_dir).resolve()

    if not findings_path.exists():
        raise FileNotFoundError(f"Findings directory not found: {findings_path}")

    summary_file = findings_path / "scan_summary.json"
    if not summary_file.exists():
        raise FileNotFoundError(
            f"No scan_summary.json in {findings_path}. "
            "Run `inspect-dataset scan ... -o <dir>` first."
        )

    summary = _load_json(summary_file)
    triage_file = findings_path / "triage.json"

    # Load all scanner findings files (one per scanner, e.g. answer_length.json)
    skip = {"scan_summary.json", "triage.json", "samples.json"}
    all_findings: list[dict[str, Any]] = []
    for f in sorted(findings_path.glob("*.json")):
        if f.name in skip:
            continue
        all_findings.extend(_load_json(f))

    # Assign stable IDs to findings if not present
    for i, finding in enumerate(all_findings):
        finding.setdefault("id", i)

    # Load or init triage state
    triage: dict[str, str] = {}
    if triage_file.exists():
        triage = _load_json(triage_file)

    app = web.Application()
    # Load samples data if available
    samples_file = findings_path / "samples.json"
    samples: list[dict[str, Any]] = []
    if samples_file.exists():
        samples = _load_json(samples_file)

    app["findings_path"] = findings_path
    app["summary"] = summary
    app["findings"] = all_findings
    app["samples"] = samples
    app["triage"] = triage
    app["triage_file"] = triage_file

    app.router.add_get("/api/summary", handle_summary)
    app.router.add_get("/api/samples", handle_samples)
    app.router.add_get("/api/findings", handle_findings)
    app.router.add_get("/api/triage", handle_get_triage)
    app.router.add_post("/api/triage", handle_post_triage)
    app.router.add_get("/api/export", handle_export)

    # Serve the SPA via WWWResource (mirrors inspect_ai pattern)
    if STATIC_DIR.exists():
        app.router.register_resource(_WWWResource())
    else:

        async def _not_built(_: web.Request) -> web.Response:
            return web.Response(
                text="Frontend not built. Run `npm run build` in _view/www/",
                content_type="text/plain",
            )

        app.router.add_get("/", _not_built)

    return app


async def handle_summary(request: web.Request) -> web.Response:
    return web.json_response(request.app["summary"])


async def handle_samples(request: web.Request) -> web.Response:
    return web.json_response(request.app["samples"])


async def handle_findings(request: web.Request) -> web.Response:
    findings = request.app["findings"]
    triage = request.app["triage"]

    # Enrich findings with triage status
    enriched = []
    for f in findings:
        entry = dict(f)
        entry["triage_status"] = triage.get(str(f["id"]), "pending")
        enriched.append(entry)

    return web.json_response(enriched)


async def handle_get_triage(request: web.Request) -> web.Response:
    return web.json_response(request.app["triage"])


async def handle_post_triage(request: web.Request) -> web.Response:
    body = await request.json()
    finding_id = str(body.get("finding_id", ""))
    status = body.get("status", "")

    if status not in ("confirmed", "dismissed", "pending"):
        return web.json_response(
            {"error": "status must be confirmed, dismissed, or pending"},
            status=400,
        )

    triage = request.app["triage"]
    if status == "pending":
        triage.pop(finding_id, None)
    else:
        triage[finding_id] = status

    _save_json(request.app["triage_file"], triage)
    return web.json_response({"ok": True})


async def handle_export(request: web.Request) -> web.Response:
    """Export sample IDs that have no confirmed findings."""
    findings = request.app["findings"]
    triage = request.app["triage"]

    # Collect sample indices with confirmed findings
    confirmed_indices: set[int] = set()
    for f in findings:
        fid = str(f["id"])
        if triage.get(fid) == "confirmed":
            idx = f.get("sample_index")
            if idx is not None:
                confirmed_indices.add(idx)

    # Get total samples from summary
    total = request.app["summary"].get("total_samples", 0)
    clean_ids = sorted(set(range(total)) - confirmed_indices)

    text = "\n".join(str(i) for i in clean_ids) + "\n"
    return web.Response(
        text=text,
        content_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=clean_ids.txt"},
    )


def run_server(findings_dir: str | Path, port: int = 7576) -> None:
    """Start the view server (blocking)."""
    app = create_app(findings_dir)
    logger.info("Starting inspect-dataset viewer on http://localhost:%d", port)
    web.run_app(app, host="localhost", port=port, print=None)
