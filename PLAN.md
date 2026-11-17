# Plan: H3 Ref2VA fast pipe — Docker Compose + MCP

## Product shape

Not a UI. A **GPU video worker** you (or an agent) call like a tool:

> “Here’s a character image + prompt → give me a short MP4.”

```text
You / Cursor agent
        │  MCP tools
        ▼
┌─────────────────┐     HTTP      ┌──────────────────────┐
│  mcp (no GPU)   │ ────────────► │  comfyui (5090)      │
│  thin wrapper   │ ◄──────────── │  Ref2VA-VSA workflow │
└─────────────────┘   poll/files  └──────────────────────┘
        │                                    │
        └──────── volumes: input / output / models ──────┘
```

**v1 scope:** compose + scripts + MCP. No studio UI, no multi-machine DiT split.

---

## Success criteria

| Gate | Pass |
| :--- | :--- |
| **G1 Smoke** | `docker compose up` → ComfyUI healthy on `:8188` |
| **G2 Models** | Download script places the 6 required files; workflow loads without missing-weight errors |
| **G3 Generate** | MCP (or CLI twin) takes image + prompt → MP4 under `./output` |
| **G4 Perf** | Warm run ≈ **≤ 2–3 min** for 5s / ~1344×768 / 124 frames on laptop 5090; peak VRAM **≤ ~16 GB** |
| **G5 Agent** | From Cursor: ask the MCP to generate from a local image path; get back path + job id |

---

## Compose services

```yaml
services:
  comfyui:          # CUDA 13 / Blackwell-capable image, --listen 0.0.0.0
  mcp:              # depends_on comfyui healthy; exposes MCP stdio or SSE
  model-pull:       # profile: tools — one-shot HF downloads into ./models
```

**Volumes (host-mounted, persist across rebuilds):**

| Host path | Container | Purpose |
| :--- | :--- | :--- |
| `./models` | ComfyUI models tree | DiT, CLIP, VAEs, LoRAs |
| `./input` | `ComfyUI/input` | Reference images for jobs |
| `./output` | `ComfyUI/output` | MP4 / previews |
| `./custom_nodes/ComfyUI-Ref2VA-VSA` | this repo (or copy) | VSA gate node |
| `./workflows` | optional | API workflow JSON |

**Env (`.env.example`):** `CUDA` image tag, HF token (optional), default width/height/length/steps/sparsity, ComfyUI URL for MCP.

**Windows note:** Docker Desktop + WSL2 + NVIDIA Container Toolkit; GPU must show up inside the `comfyui` container (`nvidia-smi`). If GPU passthrough fails, fix that before chasing model bugs.

---

## Scripts

| Script | Job |
| :--- | :--- |
| `scripts/download_models.py` | Fetch INT8 Ref2VA, NVFP4 CLIP, video/audio VAEs, Turbo LoRA, VSA gate into correct subdirs; checksum/size check |
| `scripts/healthcheck.py` | `GET /system_stats` + optional node-list check for `Ref2VAVSAGatePatch` |
| `scripts/generate.py` | CLI twin of MCP: `--image` `--prompt` `--seed` → submit API workflow → poll → print output path |
| `scripts/bench.py` | Fixed seed + sample image; log cold/warm seconds + peak VRAM note → append `benchmarks/RESULTS.md` |

`generate.py` and the MCP tool share one Python module (`pipe/comfy_client.py`) so behavior stays identical.

---

## MCP tool surface (v1)

Keep it small so an agent can’t misuse it:

| Tool | Args | Returns |
| :--- | :--- | :--- |
| `h3_health` | — | comfy up?, VRAM free?, node present? |
| `h3_generate_character_video` | `image_path` (or upload bytes path), `prompt`, optional `seed`, `width`, `height`, `length` | `job_id`, status URL hints |
| `h3_job_status` | `job_id` | `queued` / `running` / `done` / `error`, progress if available |
| `h3_get_result` | `job_id` | local `output_path`(s), duration estimate |

**Out of v1:** arbitrary workflow upload, LoRA browsing, long-form multi-clip director.

**Workflow engine:** mutate `workflows/ref2va_vsa_4step_api.json` (already API-shaped): swap prompt, seed, ref image filename, optional geometry; `POST /prompt`; poll `/history/{id}`; resolve output from history + `./output`.

---

## Implementation order

### Sprint 1 — Compose skeleton (half day)

1. `docker-compose.yml` + Dockerfile or pinned public CUDA13 ComfyUI image  
2. Mount models/input/output; bake or bind-mount this custom node  
3. Healthcheck hitting `/system_stats`  
4. `scripts/download_models.py` + documented disk budget (~40GB+)  
5. Doc: `docs/DOCKER.md` — Desktop/WSL GPU one-pager  

**Exit:** browser or curl reaches ComfyUI; models on disk.

### Sprint 2 — API generate path (half day)

1. `pipe/comfy_client.py` — upload image, patch workflow, queue, poll, fetch outputs  
2. `scripts/generate.py` CLI  
3. Smoke with sample character + fixed seed  
4. Fill first row of `benchmarks/RESULTS.md`  

**Exit:** G3 + rough G4 numbers without MCP.

### Sprint 3 — MCP wrapper (few hours)

1. Minimal MCP server (Python: `mcp` SDK) wrapping the same client  
2. Wire into Cursor MCP config (stdio to container or host process pointing at `http://localhost:8188`)  
3. Manual agent test: “make a 5s video of this image saying X”  

**Exit:** G5.

### Sprint 4 — Harden (optional)

- Timeouts, clearer OOM errors, job queue (one GPU → reject or serialize)  
- Optional Blackwell Sol-Attn as compose profile `attn-blackwell` (off by default)  
- Compose profile `bench` for automated cold/warm runs  

---

## What we will not do in v1

- Stability Matrix integration  
- Stacking Sage + Sol-Attn + VSA + H3-Optimizations together  
- GGUF path (stay on INT8 Ref2VA + Turbo + this VSA node)  
- Splitting DiT across machines  
- Fancy front-end  

---

## Risk register

| Risk | Mitigation |
| :--- | :--- |
| Windows Docker GPU flaky | Prove `nvidia-smi` in container first; WSL2 fallback if needed |
| Image lacks `sol_attn` / comfy-kitchen | Pin image known to work; or build stage that installs kitchen CUDA bits |
| Laptop 5090 power limits | Accept 2–3 min warm vs 72s desktop 4090; don’t chase parity |
| First-run model download huge | `model-pull` profile; don’t block compose `up` on download |
| Agent double-submits jobs | MCP serializes or returns “busy” while a prompt is running |

---

## Repo layout

```text
compose.yaml
.env.example
h3_mcp/Dockerfile
h3_mcp/server.py
pipe/comfy_client.py
scripts/download_models.py
scripts/generate.py
scripts/healthcheck.py
scripts/bench.py
docs/DOCKER.md
docs/MCP.md
cursor.mcp.example.json
benchmarks/RESULTS.md
data/{models,input,output,user}/
workflows/ref2va_vsa_4step_api.json
LINKS.md
PLAN.md
```

---

## Status

- **Sprint 1–3 scaffolded** (compose, download, client, CLI, MCP).
- **Next on machine:** copy `.env.example` → `.env`, download models, `docker compose up -d comfyui`, `python scripts/healthcheck.py`, then `generate.py` / wire Cursor MCP.
