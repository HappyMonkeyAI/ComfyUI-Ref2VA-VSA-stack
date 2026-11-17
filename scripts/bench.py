#!/usr/bin/env python3
"""Cold/warm timing helper — appends a row to benchmarks/RESULTS.md."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipe.comfy_client import ComfyClient, GenerateRequest

RESULTS = ROOT / "benchmarks" / "RESULTS.md"
DEFAULT_IMAGE = ROOT / "assets" / "example_character.jpg"
DEFAULT_PROMPT = (
    "A young woman smiling warmly, looking directly at the camera in a modern "
    "cozy room, high realism, detailed cinematic video."
)
DEFAULT_SEED = 981445682258077


def append_row(line: str) -> None:
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    if not RESULTS.exists():
        RESULTS.write_text(
            "# Benchmark results\n\n"
            "| when (UTC) | run | seed | WxH x frames | elapsed_s | status | outputs | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    with RESULTS.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def one_run(client: ComfyClient, label: str, image: Path, prompt: str, seed: int) -> None:
    req = GenerateRequest(image_path=image, prompt=prompt, seed=seed)
    result = client.generate(req)
    outs = ", ".join(str(p.name) for p in result.outputs) or "-"
    note = result.error.replace("|", "/") if result.error else ""
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    geom = f"{req.width}x{req.height}x{req.length}"
    row = (
        f"| {when} | {label} | {seed} | {geom} | {result.elapsed_sec:.1f} | "
        f"{result.status} | {outs} | {note} |"
    )
    append_row(row)
    print(row)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    p.add_argument("--prompt", default=DEFAULT_PROMPT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    p.add_argument("--skip-cold", action="store_true")
    args = p.parse_args()

    if not args.image.is_file():
        print(f"Missing image: {args.image}", file=sys.stderr)
        print("Copy assets/example_character.jpg or pass --image", file=sys.stderr)
        return 1

    with ComfyClient(
        base_url=args.url,
        input_dir=ROOT / "data" / "input",
        output_dir=ROOT / "data" / "output",
        timeout_sec=float(os.environ.get("H3_TIMEOUT_SEC", "900")),
    ) as client:
        if not args.skip_cold:
            one_run(client, "cold", args.image, args.prompt, args.seed)
        one_run(client, "warm", args.image, args.prompt, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
