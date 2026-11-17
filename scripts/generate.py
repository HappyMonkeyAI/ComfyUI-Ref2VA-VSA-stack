#!/usr/bin/env python3
"""CLI twin of the MCP generate tool."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipe.comfy_client import ComfyClient, GenerateRequest


def main() -> int:
    p = argparse.ArgumentParser(description="Generate a Ref2VA-VSA character video via ComfyUI API")
    p.add_argument("--image", required=True, type=Path, help="Reference character image")
    p.add_argument("--prompt", required=True, help="Motion / scene prompt")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--width", type=int, default=int(os.environ.get("H3_WIDTH", "1344")))
    p.add_argument("--height", type=int, default=int(os.environ.get("H3_HEIGHT", "768")))
    p.add_argument("--length", type=int, default=int(os.environ.get("H3_LENGTH", "124")))
    p.add_argument("--sparsity", type=float, default=float(os.environ.get("H3_SPARSITY", "0.75")))
    p.add_argument("--url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    p.add_argument(
        "--workflow",
        type=Path,
        default=Path(os.environ.get("H3_WORKFLOW", ROOT / "workflows" / "ref2va_vsa_4step_api.json")),
    )
    p.add_argument(
        "--input-dir",
        type=Path,
        default=Path(os.environ.get("H3_INPUT_DIR", ROOT / "data" / "input")),
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("H3_OUTPUT_DIR", ROOT / "data" / "output")),
    )
    p.add_argument("--timeout", type=float, default=float(os.environ.get("H3_TIMEOUT_SEC", "900")))
    args = p.parse_args()

    req = GenerateRequest(
        image_path=args.image,
        prompt=args.prompt,
        seed=args.seed,
        width=args.width,
        height=args.height,
        length=args.length,
        sparsity=args.sparsity,
    )

    with ComfyClient(
        base_url=args.url,
        workflow_path=args.workflow,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        timeout_sec=args.timeout,
    ) as client:
        result = client.generate(req)

    payload = {
        "job_id": result.job_id,
        "status": result.status,
        "elapsed_sec": round(result.elapsed_sec, 2),
        "outputs": [str(p) for p in result.outputs],
        "error": result.error,
    }
    print(json.dumps(payload, indent=2))
    return 0 if result.status == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
