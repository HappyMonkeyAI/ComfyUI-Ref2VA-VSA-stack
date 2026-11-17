#!/usr/bin/env python3
"""Download MiniMax H3 Ref2VA-VSA required checkpoints into a ComfyUI models tree."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

# Current Comfy-Org layout (Nov 2026): Comfy-Org/MiniMax-H3
MODELS: list[dict[str, str]] = [
    {
        "repo_id": "Comfy-Org/MiniMax-H3",
        "filename": "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
        "subdir": "diffusion_models",
        "dest_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    },
    {
        "repo_id": "Comfy-Org/MiniMax-H3",
        "filename": "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "subdir": "text_encoders",
        "dest_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    },
    {
        "repo_id": "Comfy-Org/MiniMax-H3",
        "filename": "vae/minimax_h3_video_vae_int8_convrot.safetensors",
        "subdir": "vae",
        "dest_name": "minimax_h3_video_vae_int8_convrot.safetensors",
    },
    {
        "repo_id": "Comfy-Org/MiniMax-H3",
        "filename": "vae/minimax_h3_audio_vae_fp32.safetensors",
        "subdir": "vae",
        "dest_name": "minimax_h3_audio_vae_fp32.safetensors",
    },
    {
        "repo_id": "Comfy-Org/MiniMax-H3",
        "filename": "loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
        "subdir": "loras",
        "dest_name": "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
    },
    {
        "repo_id": "barelymining/ComfyUI-MiniMax-H3-FastVideo",
        "filename": "fasth3_vsa_gate.safetensors",
        "subdir": "loras",
        "dest_name": "fasth3_vsa_gate.safetensors",
    },
]


def models_root() -> Path:
    raw = os.environ.get("H3_MODELS_DIR") or os.environ.get("COMFYUI_MODELS_DIR")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parent.parent / "data" / "models"


def hf_token() -> str | None:
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def ensure_link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    try:
        os.link(src, dest)
    except OSError:
        dest.write_bytes(src.read_bytes())


def main() -> int:
    # Classic HTTP downloads resume more reliably on Windows than Xet for multi-GB files.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    root = models_root()
    root.mkdir(parents=True, exist_ok=True)
    token = hf_token()
    print(f"Models root: {root}")
    print(f"HF auth: {'token set' if token else 'anonymous (public repos only)'}")
    print(f"Will download {len(MODELS)} files (tens of GB — be patient).\n")

    for item in MODELS:
        dest = root / item["subdir"] / item["dest_name"]
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            print(f"[skip] {dest.name} ({dest.stat().st_size / 1e9:.2f} GB)")
            continue
        print(f"[get ] {item['repo_id']} :: {item['filename']}")
        try:
            cached = hf_hub_download(
                repo_id=item["repo_id"],
                filename=item["filename"],
                token=token,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[fail] {exc}", file=sys.stderr)
            print(
                "\nIf this is 401/403: create a read token at https://huggingface.co/settings/tokens\n"
                "then set HF_TOKEN in .env (no empty value) or run: huggingface-cli login",
                file=sys.stderr,
            )
            return 1
        ensure_link_or_copy(Path(cached), dest)
        print(f"[ok  ] {dest} ({dest.stat().st_size / 1e9:.2f} GB)")

    print("\nDone. Point ComfyUI models volume at:", root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
