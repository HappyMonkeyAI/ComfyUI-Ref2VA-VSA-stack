#!/usr/bin/env python3
"""stdio MCP server: character image + prompt → short Ref2VA-VSA video via ComfyUI."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

from pipe.comfy_client import ComfyClient, GenerateRequest

app = FastMCP("ref2va-vsa")

_jobs: dict[str, dict[str, Any]] = {}


def _client() -> ComfyClient:
    return ComfyClient(
        base_url=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"),
        workflow_path=Path(
            os.environ.get(
                "H3_WORKFLOW",
                str(ROOT / "workflows" / "ref2va_vsa_4step_api.json"),
            )
        ),
        input_dir=Path(os.environ.get("H3_INPUT_DIR", ROOT / "data" / "input")),
        output_dir=Path(os.environ.get("H3_OUTPUT_DIR", ROOT / "data" / "output")),
        timeout_sec=float(os.environ.get("H3_TIMEOUT_SEC", "900")),
    )


@app.tool()
def h3_health() -> str:
    """Check ComfyUI reachability, VRAM stats, and Ref2VA-VSA node registration."""
    with _client() as client:
        try:
            return json.dumps(client.health(), indent=2, default=str)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"ok": False, "error": str(exc)})


@app.tool()
def h3_generate_character_video(
    image_path: str,
    prompt: str,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    length: int | None = None,
    wait: bool = True,
) -> str:
    """
    Generate a short character-locked video from a reference image using MiniMax H3 Ref2VA-VSA.

    Args:
        image_path: Absolute or workspace-relative path to the character reference image.
        prompt: Scene / motion description.
        seed: Optional fixed seed for reproducibility.
        width: Frame width (default from env H3_WIDTH or 1344).
        height: Frame height (default H3_HEIGHT or 768).
        length: Frame count (default H3_LENGTH or 124 ≈ 5s @ 24fps).
        wait: If true, block until done and return output paths; if false, return job_id only.
    """
    path = Path(image_path)
    if not path.is_file():
        return json.dumps({"ok": False, "error": f"image not found: {image_path}"})

    req = GenerateRequest(
        image_path=path,
        prompt=prompt,
        seed=seed,
        width=int(width if width is not None else os.environ.get("H3_WIDTH", "1344")),
        height=int(height if height is not None else os.environ.get("H3_HEIGHT", "768")),
        length=int(length if length is not None else os.environ.get("H3_LENGTH", "124")),
        sparsity=float(os.environ.get("H3_SPARSITY", "0.75")),
    )

    with _client() as client:
        if not wait:
            image_name = client.upload_image(req.image_path)
            workflow = client.build_workflow(req, image_name)
            job_id = client.queue_prompt(workflow)
            _jobs[job_id] = {"prompt": prompt, "image": str(path)}
            return json.dumps({"ok": True, "job_id": job_id, "status": "queued"})

        if client.is_busy():
            return json.dumps(
                {
                    "ok": False,
                    "error": "GPU busy: a job is already running. Use h3_job_status or wait.",
                }
            )

        result = client.generate(req)
        _jobs[result.job_id] = {
            "prompt": prompt,
            "image": str(path),
            "outputs": [str(p) for p in result.outputs],
        }
        return json.dumps(
            {
                "ok": result.status == "done",
                "job_id": result.job_id,
                "status": result.status,
                "elapsed_sec": round(result.elapsed_sec, 2),
                "outputs": [str(p) for p in result.outputs],
                "error": result.error,
            },
            indent=2,
        )


@app.tool()
def h3_job_status(job_id: str) -> str:
    """Poll a previously queued generation job."""
    with _client() as client:
        status = client.job_status(job_id)
    return json.dumps(
        {
            "job_id": status.job_id,
            "status": status.status,
            "detail": status.detail,
            "outputs": status.outputs,
        },
        indent=2,
    )


@app.tool()
def h3_get_result(job_id: str) -> str:
    """Resolve output file paths for a completed job."""
    with _client() as client:
        status = client.job_status(job_id)
        if status.status != "done":
            return json.dumps(
                {
                    "ok": False,
                    "job_id": job_id,
                    "status": status.status,
                    "detail": status.detail,
                },
                indent=2,
            )
        paths = client.resolve_output_paths(status.outputs)
    return json.dumps(
        {
            "ok": True,
            "job_id": job_id,
            "status": "done",
            "outputs": [str(p) for p in paths],
        },
        indent=2,
    )


def main() -> None:
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
