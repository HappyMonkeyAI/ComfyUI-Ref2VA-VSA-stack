#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipe.comfy_client import ComfyClient


def main() -> int:
    url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    with ComfyClient(base_url=url) as client:
        try:
            payload = client.health()
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1
    print(json.dumps(payload, indent=2, default=str))
    if not payload.get("has_ref2va_vsa_node"):
        print(
            "\nWARN: Ref2VAVSAGatePatch node not registered. "
            "Check custom_nodes mount and ComfyUI logs.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
