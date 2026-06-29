from __future__ import annotations

import argparse
import base64
import json
import urllib.request

from .config import load_config


RED_DOT_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_smoke(config_path: str | None = None) -> int:
    config = load_config(config_path)
    bridge = config.bridge
    local_id = str(config.local_model.get("id") or "local/gemma")
    base = f"http://{bridge.host}:{bridge.port}/v1/responses"
    text = post_json(base, {"model": local_id, "input": "Reply exactly OK and nothing else.", "max_output_tokens": 32, "temperature": 0.2})
    print("text:", text.get("output_text"))
    data_url = "data:image/png;base64," + base64.b64encode(base64.b64decode(RED_DOT_PNG)).decode("ascii")
    vision = post_json(
        base,
        {
            "model": local_id,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "What is the dominant color in this image? Answer with one word only."},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            "max_output_tokens": 32,
            "temperature": 0.2,
        },
    )
    print("vision:", vision.get("output_text"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args(argv)
    return run_smoke(args.config)

