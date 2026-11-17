# MCP tools — Ref2VA-VSA

Agent-facing tools exposed by `python -m h3_mcp.server` (stdio).

| Tool | Purpose |
| :--- | :--- |
| `h3_health` | ComfyUI up? VRAM? `Ref2VAVSAGatePatch` registered? |
| `h3_generate_character_video` | image path + prompt → MP4 (optional seed / size / `wait`) |
| `h3_job_status` | Poll `job_id` |
| `h3_get_result` | Resolve output paths for a completed job |

Typical agent flow:

1. `h3_health`
2. `h3_generate_character_video(image_path=..., prompt=..., wait=true)`
3. Read `outputs[0]` from the JSON result

With `wait=false`, poll via `h3_job_status` then `h3_get_result`.

See [DOCKER.md](./DOCKER.md) for Cursor `mcpServers` config.
