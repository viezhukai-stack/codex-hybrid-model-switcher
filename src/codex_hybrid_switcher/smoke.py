from __future__ import annotations

import argparse
import base64
import json
import re
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


def output_matches(text: object, expected: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()
    wanted = re.sub(r"[^a-z0-9]+", " ", expected.lower()).strip()
    return bool(wanted and wanted in normalized.split()) or normalized == wanted


def run_smoke(
    config_path: str | None = None,
    *,
    skip_vision: bool = False,
    expect_text: str = "OK",
    expect_vision: str = "red",
) -> int:
    config = load_config(config_path)
    bridge = config.bridge
    local_id = str(config.local_model.get("id") or "local/gemma")
    base = f"http://{bridge.host}:{bridge.port}/v1/responses"
    text = post_json(base, {"model": local_id, "input": "Reply exactly OK and nothing else.", "max_output_tokens": 32, "temperature": 0.2})
    text_out = text.get("output_text")
    print("text:", text_out)
    ok = output_matches(text_out, expect_text)
    if skip_vision:
        return 0 if ok else 1

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
    vision_out = vision.get("output_text")
    print("vision:", vision_out)
    if not output_matches(vision_out, expect_vision):
        ok = False
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    parser.add_argument("--skip-vision", action="store_true")
    parser.add_argument("--expect-text", default="OK")
    parser.add_argument("--expect-vision", default="red")
    args = parser.parse_args(argv)
    return run_smoke(args.config, skip_vision=args.skip_vision, expect_text=args.expect_text, expect_vision=args.expect_vision)
