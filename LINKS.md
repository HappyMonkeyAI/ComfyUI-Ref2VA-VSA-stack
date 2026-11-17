# MiniMax H3 / Ref2VA — Useful Links

Curated for a **24 GB RTX 5090** laptop aiming at fast local character video (Ref2VA), with Docker and multi-machine options as follow-ons.

---

## Install order (recommended)

Do these in sequence. Get a warm 5s Ref2VA clip working before adding extras.

1. **ComfyUI 0.30+** with native MiniMax H3 support (CUDA 13 / recent PyTorch for Blackwell).
2. **Models** (Comfy-Org + Turbo LoRA + VSA gate) — see this repo’s README table.
3. **This node:** [Kablex/ComfyUI-Ref2VA-VSA](https://github.com/Kablex/ComfyUI-Ref2VA-VSA)
4. Load `workflows/ref2va_vsa_4step_rtx4090.json`, generate once cold + once warm, note VRAM/time.
5. Optional on 5090: [KingGore/ComfyUI_sol-attn_Blackwell](https://github.com/KingGore/ComfyUI_sol-attn_Blackwell) — **only if** Ref2VA-VSA’s `sol_attn` path is missing/slow; do not stack blind.
6. Optional VRAM knobs: [Zironic/H3-Optimizations](https://github.com/Zironic/H3-Optimizations)
7. Optional Docker after native works: experiment-lab or RunPod minimax image (below).

### Don’t combine (unless you’ve measured both ways)

| Avoid stacking | Why |
| :--- | :--- |
| Ref2VA-VSA + FastH3-VSA T2VA patch | Different checkpoints / conditioning modes |
| Ref2VA-VSA + SageAttention + another Sol-Attn patch + H3 sparse node | Competing attention backends; often slower or broken |
| Turbo LoRA on a FastH3 **VSA-trained** T2VA checkpoint that already is 4-step | Double-distill / wrong sigma ladder |
| GGUF Q4 DiT + this repo’s VSA gate transplant | Gate expects the INT8 Ref2VA ConvRot backbone path |
| Dense Turbo-only workflow + VSA gate without this patch | Gate alone does nothing useful without the layout patch |

**Safe baseline stack:** INT8 Ref2VA pruned + Turbo 4-step LoRA + `fasth3_vsa_gate` via **this** node + NVFP4 text encoder + FP16 video VAE.

---

## Core speed / VRAM

| Project | Notes | URL |
| :--- | :--- | :--- |
| **ComfyUI-Ref2VA-VSA** | Character Ref2VA + VSA gate transplant; ~72s / 5s on 4090 | https://github.com/Kablex/ComfyUI-Ref2VA-VSA |
| **H3-Optimizations** | Memory + sparse / VSA attention nodes | https://github.com/Zironic/H3-Optimizations |
| **ComfyUI_sol-attn_Blackwell** | Sol-Attn for RTX 5090 (SM120) | https://github.com/KingGore/ComfyUI_sol-attn_Blackwell |
| **ComfyUI-FastH3-VSA** | FastH3 VSA for **T2VA** (not Ref2VA) | https://github.com/exportAnything/ComfyUI-FastH3-VSA |
| **minimax-h3-enhanced-loader-star7** | Loader for official / quant / FastH3 / VSA variants | https://github.com/star7code/minimax-h3-enhanced-loader-star7 |

---

## Models & checkpoints

| Resource | Notes | URL |
| :--- | :--- | :--- |
| Comfy-Org MiniMax H3 repackaged | INT8 DiT, NVFP4 encoder, VAEs | https://huggingface.co/Comfy-Org/MiniMax_H3_repackaged |
| Ref2VA INT8 ConvRot DiT | Required backbone for this node | https://huggingface.co/Comfy-Org/MiniMax_H3_repackaged/resolve/main/split_files/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors |
| FastH3 VSA gate | `fasth3_vsa_gate.safetensors` | https://huggingface.co/barelymining/ComfyUI-MiniMax-H3-FastVideo/resolve/main/fasth3_vsa_gate.safetensors |
| LightX2V Turbo 4-step LoRA | Most of the wall-clock win | https://huggingface.co/lightx2v/Minimax-h3-Turbo |
| FastVideo / FastH3 | Upstream VSA / 4-step distillation | https://github.com/hao-ai-lab/FastVideo |
| GGUF pruned H3 (optional) | Lower VRAM; not the VSA-Ref2VA path | https://huggingface.co/Abiray/MiniMax-H3-Pruned-GGUF |
| Unsloth H3 GGUF range | Q2–Q8 ladder + encoder GGUFs | https://comfyui-wiki.com/en/news/2026-08-10-unsloth-minimax-h3-gguf |
| VRAM calculator | INT8 / NVFP4 / GGUF sizing | https://modelvram.com/minimax-h3-vram-calculator/ |

---

## Docker / deploy

| Project | Notes | URL |
| :--- | :--- | :--- |
| **minimax-h3-experiment-lab** | Reproducible docker-compose H3 lab | https://github.com/Sunwood-ai-labs/minimax-h3-experiment-lab |
| **run-comfyui-minimax** | RunPod image; Blackwell vs standard profiles | https://github.com/jalberty2018/run-comfyui-minimax |
| **h3-bootstrap** | Bootstrap ComfyUI + Ref2VA-VSA on a pod | https://github.com/Gamma-Burst/h3-bootstrap |
| **comfyui-blackwell-docker** | Generic Blackwell ComfyUI compose | https://github.com/ChiefNakor/comfyui-blackwell-docker |
| clasyc/comfyui (Docker Hub) | CUDA 13.1 / 5090-oriented image | https://hub.docker.com/r/clasyc/comfyui |

---

## Multi-machine / long video / quality extras

| Project | Notes | URL |
| :--- | :--- | :--- |
| **minimax_h3_t4** | Two-GPU H3 extension | https://github.com/StanLukuvka/minimax_h3_t4 |
| **jayce-recast-video-dgx** | Multi-machine character replace pipeline | https://github.com/JayceHuang/jayce-recast-video-dgx |
| **Comfyui_Minimax_h3_latent_Upscaler** | Latent upscale without VAE round-trip | https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler |
| **ComfyUI_MiniMaxH3_Director** | Multi-segment director | https://github.com/AIMixer/ComfyUI_MiniMaxH3_Director |
| ComfyUI-H3-Auto-Director | Multi-segment + resume/assembly | https://github.com/kongbai-0421/ComfyUI-H3-Auto-Director |
| MiniMax-H3-All-in-One-Video-Studio | REF2VA / T2VA / I2V / FLF2VA pack | https://github.com/fukkun2705-commits/MiniMax-H3-All-in-One-Video-Studio |
| ComfyUI-H3-SeedHunter-LongForm | Preview → refine → long AV continue | https://github.com/MaartenAlbers/ComfyUI-H3-SeedHunter-LongForm |

---

## Indexes & workflow packs

| Project | Notes | URL |
| :--- | :--- | :--- |
| **awesome-minimax-h3-integration** | Official-ish community index (nodes, quants, TRT, OrbitQuant, VDN, …) | https://github.com/MiniMax-AI/awesome-minimax-h3-integration |
| **minimax_h3_workflows** | FastH3 VSA + FastVAE measured workflows | https://github.com/sepiablue-ai/minimax_h3_workflows |
| **awesome-ai-video** | Broader AI video production index (incl. H3) | https://github.com/zhaotoday/awesome-ai-video |
| ChrisJohnson89/minimax-h3-comfyui | Fast pruned T2V/I2V workflows + benchmarks | https://github.com/ChrisJohnson89/minimax-h3-comfyui |
| FlowForgeLabAi/MiniMax-H3-8GB-Workflows | Low-VRAM laptop notes (restart-every-run evidence) | https://github.com/FlowForgeLabAi/MiniMax-H3-8GB-Workflows |
| win520-1206/ComfyUI-H3-LowVRAM-Workflows | 8 GB–oriented H3 workflows | https://github.com/win520-1206/ComfyUI-H3-LowVRAM-Workflows |

---

## Background reading

| Piece | Notes | URL |
| :--- | :--- | :--- |
| SnackOnAI deep dive | What the 9× really comes from (Turbo vs sparsity) | https://www.snackonai.com/p/comfyui-ref2va-vsa-proves-a-sparse-attention-gate-can-be-transplanted-and-most-of-the-speedup-comes |
| RexxuLabs setup guide | Practical Ref2VA-VSA install notes | https://rexxulabs.com/blogs/ultra-fast-character-video-generation-with-comfyui-ref2va-vsa |
| RunPod 5090 H3 writeup | CUDA 13 image + dynamic offload on 5090 | https://media.zeneffi.co.jp/posts/minimax-h3-runpod-rtx5090 |
| vLLM MiniMax-H3 recipe | Server-side FastH3 / VSA (multi-GPU USP) | https://github.com/vllm-project/recipes/blob/main/models/MiniMaxAI/MiniMax-H3.yaml |

---

## Other related finds (lower priority)

| Project | Notes | URL |
| :--- | :--- | :--- |
| TianyiDataScience/MiniMax-H3-OneClick | One-click H3 + ComfyUI install | https://github.com/TianyiDataScience/MiniMax-H3-OneClick |
| yume-arasaki/ezlaunch-minimax-h3 | Double-click Turbo installer | https://github.com/yume-arasaki/ezlaunch-minimax-h3 |
| matlowai/ComfyUI-MAINodes | Contact-sheet + motion lab nodes | https://github.com/matlowai/ComfyUI-MAINodes |
| shuaixn/ComfyUI-MiniMaxH3DualClockSampler | Dual-clock Euler for Turbo AV | https://github.com/shuaixn/ComfyUI-MiniMaxH3DualClockSampler |
| wuli-art/MiniMax-H3-Turbo-ComfyUI | Turbo workflow pack | https://github.com/wuli-art/MiniMax-H3-Turbo-ComfyUI |
| PlaTuring/Relay | Windows local H3/ComfyUI project manager | https://github.com/PlaTuring/Relay |
| siyuan-liu31/minimax-h3-video-studio | Visual studio UI over H3 + ComfyUI | https://github.com/siyuan-liu31/minimax-h3-video-studio |
| pwillia7/sorant | Web front end; GPU stays local | https://github.com/pwillia7/sorant |

---

---

## This repo’s plan

| Doc | Purpose |
| :--- | :--- |
| [PLAN.md](./PLAN.md) | Docker Compose + MCP build/test plan (image → short MP4 tool) |
| [docs/DOCKER.md](./docs/DOCKER.md) | Compose up, model pull, GPU notes |
| [docs/MCP.md](./docs/MCP.md) | MCP tool list + agent flow |
| [cursor.mcp.example.json](./cursor.mcp.example.json) | Example Cursor MCP config |

*Generated for local reference. Prefer the “Core speed / VRAM” + “Don’t combine” sections when wiring a first working pipe.*
