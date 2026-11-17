# Docker — Ref2VA-VSA fast pipe

## Prerequisites

- Docker Desktop (Windows) with **WSL2** backend
- NVIDIA driver that supports your **RTX 5090** + container GPU
- NVIDIA Container Toolkit / Docker GPU support (`docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi`)
- **~50 GB+** free disk for models

## Quick start

```powershell
cd C:\Users\steph\Documents\development\ComfyUI-Ref2VA-VSA
copy .env.example .env

# Create data dirs
mkdir data\models, data\input, data\output, data\user -Force

# Pull models (large — tens of GB). Host Python or compose profile:
python -m pip install -r requirements-pipe.txt
python scripts\download_models.py
# or: docker compose --profile tools run --rm model-pull

# Start ComfyUI (GPU)
docker compose up -d comfyui

# Health (needs Ref2VA-VSA node mounted)
docker compose --profile tools run --rm health
# or: python scripts\healthcheck.py
```

UI/API: http://127.0.0.1:8188

If the image’s ComfyUI path is not `/app/ComfyUI`, set `COMFYUI_HOME` in `.env` to match (`docker compose exec comfyui ls /`).

## Generate without MCP

```powershell
python scripts\generate.py `
  --image .\assets\example_character.jpg `
  --prompt "A young woman smiling warmly, looking at the camera in a cozy room." `
  --seed 981445682258077
```

## Benchmark

```powershell
python scripts\bench.py
# appends to benchmarks\RESULTS.md
```

## Cursor MCP (host-side, recommended)

Keep `comfyui` in Docker; run the MCP on the host so Cursor can speak stdio:

```json
{
  "mcpServers": {
    "ref2va-vsa": {
      "command": "python",
      "args": ["-m", "h3_mcp.server"],
      "cwd": "C:\\Users\\steph\\Documents\\development\\ComfyUI-Ref2VA-VSA",
      "env": {
        "COMFYUI_URL": "http://127.0.0.1:8188",
        "H3_INPUT_DIR": "C:\\Users\\steph\\Documents\\development\\ComfyUI-Ref2VA-VSA\\data\\input",
        "H3_OUTPUT_DIR": "C:\\Users\\steph\\Documents\\development\\ComfyUI-Ref2VA-VSA\\data\\output",
        "PYTHONPATH": "C:\\Users\\steph\\Documents\\development\\ComfyUI-Ref2VA-VSA"
      }
    }
  }
}
```

Install deps once: `pip install -r requirements-pipe.txt`

## Image choice

Default: `ghcr.io/pixeloven/comfyui/complete:cuda-sm120-latest` (Blackwell / SM120).

Alternatives in `.env` → `COMFYUI_IMAGE`:

- `clasyc/comfyui:cuda13.1`
- `runpod/comfyui:slim-5090` (if available on your registry)

Pin a digest once you find a working tag.

## GPU not visible?

1. `docker compose exec comfyui nvidia-smi`
2. Confirm WSL2 + GPU in Docker Desktop settings
3. Update NVIDIA driver (CUDA 13-capable)

## Don’t stack attention patches

v1 uses **this repo’s Ref2VA-VSA node only**. Do not also enable SageAttention + Sol-Attn + H3-Optimizations until you A/B them.
