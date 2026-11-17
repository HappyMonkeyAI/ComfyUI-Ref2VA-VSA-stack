from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

DEFAULT_WORKFLOW = (
    Path(__file__).resolve().parent.parent / "workflows" / "ref2va_vsa_4step_api.json"
)


@dataclass
class GenerateRequest:
    image_path: Path
    prompt: str
    seed: int | None = None
    width: int = 1344
    height: int = 768
    length: int = 124
    sparsity: float = 0.75
    filename_prefix: str = "video/h3_ref2va_vsa"


@dataclass
class JobStatus:
    job_id: str
    status: str  # queued | running | done | error | unknown
    detail: str = ""
    outputs: list[str] = field(default_factory=list)


@dataclass
class GenerateResult:
    job_id: str
    status: str
    outputs: list[Path]
    elapsed_sec: float
    error: str = ""


class ComfyClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8188",
        workflow_path: Path | None = None,
        input_dir: Path | None = None,
        output_dir: Path | None = None,
        timeout_sec: float = 900.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.workflow_path = Path(workflow_path) if workflow_path else DEFAULT_WORKFLOW
        self.input_dir = Path(input_dir) if input_dir else None
        self.output_dir = Path(output_dir) if output_dir else None
        self.timeout_sec = timeout_sec
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ComfyClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        stats = self._client.get("/system_stats").json()
        object_info_ok = False
        has_vsa_node = False
        try:
            info = self._client.get("/object_info/Ref2VAVSAGatePatch").json()
            object_info_ok = True
            has_vsa_node = "Ref2VAVSAGatePatch" in info
        except Exception as exc:  # noqa: BLE001 — surface in payload
            info_error = str(exc)
        else:
            info_error = ""
        return {
            "ok": True,
            "base_url": self.base_url,
            "system_stats": stats,
            "object_info_ok": object_info_ok,
            "has_ref2va_vsa_node": has_vsa_node,
            "object_info_error": info_error,
        }

    def upload_image(self, image_path: Path, overwrite: bool = True) -> str:
        image_path = Path(image_path)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Prefer ComfyUI upload API so the LoadImage node can see the file.
        with image_path.open("rb") as fh:
            files = {
                "image": (image_path.name, fh, "application/octet-stream"),
            }
            data = {"overwrite": "true" if overwrite else "false"}
            resp = self._client.post("/upload/image", files=files, data=data)
            resp.raise_for_status()
            payload = resp.json()
            name = payload.get("name") or image_path.name
            # Also mirror into shared input dir when provided (compose volumes).
            if self.input_dir is not None:
                self.input_dir.mkdir(parents=True, exist_ok=True)
                dest = self.input_dir / Path(name).name
                if dest.resolve() != image_path.resolve():
                    shutil.copy2(image_path, dest)
            return str(name)

    def build_workflow(self, req: GenerateRequest, image_name: str) -> dict[str, Any]:
        workflow = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        seed = req.seed if req.seed is not None else uuid.uuid4().int & ((1 << 63) - 1)

        if "6" in workflow:
            workflow["6"]["inputs"]["prompt"] = req.prompt
            workflow["6"]["inputs"]["width"] = int(req.width)
            workflow["6"]["inputs"]["height"] = int(req.height)
            workflow["6"]["inputs"]["length"] = int(req.length)
        if "8" in workflow:
            workflow["8"]["inputs"]["noise_seed"] = int(seed)
        if "50" in workflow:
            workflow["50"]["inputs"]["image"] = image_name
        if "144" in workflow:
            workflow["144"]["inputs"]["sparsity"] = float(req.sparsity)
        if "16" in workflow:
            workflow["16"]["inputs"]["filename_prefix"] = req.filename_prefix
        return workflow

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        client_id = str(uuid.uuid4())
        resp = self._client.post(
            "/prompt",
            json={"prompt": workflow, "client_id": client_id},
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"ComfyUI rejected prompt: {data['error']}")
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"No prompt_id in response: {data}")
        return str(prompt_id)

    def queue_snapshot(self) -> dict[str, Any]:
        return self._client.get("/queue").json()

    def is_busy(self) -> bool:
        try:
            queue = self.queue_snapshot()
        except Exception:
            return False
        return bool(queue.get("queue_running"))

    def job_status(self, job_id: str) -> JobStatus:
        try:
            queue = self.queue_snapshot()
        except Exception as exc:  # noqa: BLE001
            return JobStatus(job_id=job_id, status="unknown", detail=str(exc))

        for item in queue.get("queue_running", []) or []:
            if len(item) > 1 and str(item[1]) == job_id:
                return JobStatus(job_id=job_id, status="running")
        for item in queue.get("queue_pending", []) or []:
            if len(item) > 1 and str(item[1]) == job_id:
                return JobStatus(job_id=job_id, status="queued")

        hist = self._client.get(f"/history/{job_id}").json()
        entry = hist.get(job_id)
        if not entry:
            return JobStatus(job_id=job_id, status="unknown", detail="not in queue or history")

        status_blob = entry.get("status") or {}
        if status_blob.get("status_str") == "error" or status_blob.get("completed") is False:
            messages = status_blob.get("messages") or []
            return JobStatus(job_id=job_id, status="error", detail=str(messages))

        outputs = self._collect_output_names(entry)
        if outputs or status_blob.get("completed") is True:
            return JobStatus(job_id=job_id, status="done", outputs=outputs)

        return JobStatus(job_id=job_id, status="running", detail="in history, not marked complete")

    def wait_for_job(self, job_id: str, poll_sec: float = 2.0) -> JobStatus:
        deadline = time.monotonic() + self.timeout_sec
        last = JobStatus(job_id=job_id, status="unknown")
        while time.monotonic() < deadline:
            last = self.job_status(job_id)
            if last.status in {"done", "error"}:
                return last
            time.sleep(poll_sec)
        last.status = "error"
        last.detail = f"timed out after {self.timeout_sec:.0f}s"
        return last

    def resolve_output_paths(self, names: list[str]) -> list[Path]:
        if not self.output_dir:
            return [Path(n) for n in names]
        found: list[Path] = []
        for name in names:
            direct = self.output_dir / name
            if direct.is_file():
                found.append(direct)
                continue
            # SaveVideo often nests under subdirs / adds suffixes — search by basename.
            base = Path(name).name
            matches = sorted(self.output_dir.rglob(base))
            if matches:
                found.extend(matches)
            else:
                # Fuzzy: prefix match for video_*_00001.mp4 style
                stem = Path(base).stem
                fuzzy = [
                    p
                    for p in self.output_dir.rglob("*")
                    if p.is_file() and stem in p.name and p.suffix.lower() in {".mp4", ".webm", ".mkv"}
                ]
                found.extend(sorted(fuzzy))
        # de-dupe
        uniq: list[Path] = []
        seen: set[str] = set()
        for p in found:
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                uniq.append(p)
        return uniq

    def generate(self, req: GenerateRequest) -> GenerateResult:
        t0 = time.monotonic()
        image_name = self.upload_image(req.image_path)
        workflow = self.build_workflow(req, image_name)
        job_id = self.queue_prompt(workflow)
        status = self.wait_for_job(job_id)
        elapsed = time.monotonic() - t0
        if status.status != "done":
            return GenerateResult(
                job_id=job_id,
                status=status.status,
                outputs=[],
                elapsed_sec=elapsed,
                error=status.detail or "generation failed",
            )
        paths = self.resolve_output_paths(status.outputs)
        return GenerateResult(
            job_id=job_id,
            status="done",
            outputs=paths,
            elapsed_sec=elapsed,
        )

    @staticmethod
    def _collect_output_names(history_entry: dict[str, Any]) -> list[str]:
        names: list[str] = []
        outputs = history_entry.get("outputs") or {}
        for node_out in outputs.values():
            if not isinstance(node_out, dict):
                continue
            for key in ("gifs", "videos", "images", "audio"):
                for item in node_out.get(key) or []:
                    if isinstance(item, dict) and "filename" in item:
                        sub = item.get("subfolder") or ""
                        fn = item["filename"]
                        names.append(f"{sub}/{fn}" if sub else fn)
        return names
