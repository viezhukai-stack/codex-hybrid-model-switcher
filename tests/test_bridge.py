from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from codex_hybrid_switcher.bridge import (
    bridge_model_ids,
    chat_parts_from_content,
    clean_local_text,
    image_url_from_part,
    local_llama_command,
    optional_llama_args,
    responses_input_to_messages,
)
from codex_hybrid_switcher.config import AppConfig


def test_clean_local_text_removes_channel_artifacts():
    text = "<|channel|>analysis <|message|>OK<|end|><end_of_turn>"

    assert clean_local_text(text) == "OK"


def test_image_url_from_base64_part():
    part = {"type": "input_image", "b64_json": "abcd", "media_type": "image/jpeg"}

    assert image_url_from_part(part) == "data:image/jpeg;base64,abcd"


def test_chat_parts_from_content_preserves_user_images():
    content = [
        {"type": "input_text", "text": "What color?"},
        {"type": "input_image", "image_url": "data:image/png;base64,abcd"},
    ]

    parts = chat_parts_from_content(content, allow_images=True)

    assert parts == [
        {"type": "text", "text": "What color?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abcd"}},
    ]


def test_chat_parts_from_content_drops_images_when_disallowed():
    content = [
        {"type": "output_text", "text": "Assistant text"},
        {"type": "input_image", "image_url": "data:image/png;base64,abcd"},
    ]

    parts = chat_parts_from_content(content, allow_images=False)

    assert parts == [{"type": "text", "text": "Assistant text"}]


def test_responses_input_to_messages_maps_multimodal_user_content():
    req = {
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Describe this"},
                    {"type": "input_image", "image_url": "data:image/png;base64,abcd"},
                ],
            }
        ]
    }

    messages = responses_input_to_messages(req, "System prompt")

    assert messages[0] == {"role": "system", "content": "System prompt"}
    assert messages[1]["role"] == "user"
    assert messages[1]["content"][0] == {"type": "text", "text": "Describe this"}
    assert messages[1]["content"][1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,abcd"}}


def test_bridge_models_only_include_routeable_cloud_and_official_fallback(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {"id": "openai-official", "kind": "official", "model": "gpt-5.5"},
                {"id": "cloud-gpt-main", "kind": "cloud", "model": "gpt-5.4", "route": "bridge"},
            ],
            "local_model": {"id": "local/gemma"},
        },
    )

    assert bridge_model_ids(config) == ["gpt-5.5", "gpt-5.4"]


def test_bridge_models_include_local_only_when_local_provider_exists(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {"id": "cloud-gpt-main", "kind": "cloud", "model": "gpt-5.4", "route": "bridge"},
                {"id": "local-gemma", "kind": "local", "model": "local/gemma"},
            ],
            "local_model": {"id": "local/gemma"},
        },
    )

    assert bridge_model_ids(config) == ["gpt-5.4", "local/gemma"]


def test_bridge_models_do_not_advertise_official_fallback_for_multiple_bridge_clouds(tmp_path):
    config = AppConfig(
        tmp_path / "config.json",
        {
            "providers": [
                {"id": "openai-official", "kind": "official", "model": "gpt-5.5"},
                {"id": "cloud-a", "kind": "cloud", "model": "provider-a", "route": "bridge"},
                {"id": "cloud-b", "kind": "cloud", "model": "provider-b", "route": "bridge"},
            ],
        },
    )

    assert bridge_model_ids(config) == ["provider-a", "provider-b"]


def test_optional_llama_args_support_low_vram_multimodal_tuning():
    args = optional_llama_args(
        {
            "gpu_layers": 0,
            "parallel_slots": 1,
            "threads": 6,
            "threads_batch": 6,
            "batch_size": 128,
            "ubatch_size": 64,
            "flash_attn": "auto",
            "fit": "on",
            "op_offload": False,
            "mmproj_offload": False,
        }
    )

    assert "-ngl" in args
    assert args[args.index("-ngl") + 1] == "0"
    assert "--batch-size" in args
    assert args[args.index("--batch-size") + 1] == "128"
    assert "--ubatch-size" in args
    assert args[args.index("--ubatch-size") + 1] == "64"
    assert "--no-op-offload" in args
    assert "--no-mmproj-offload" in args


def test_local_llama_command_uses_structured_args_before_extra_args():
    bridge = SimpleNamespace(host="127.0.0.1", llama_port=19031)
    local = {
        "ctx_size": 512,
        "gpu_layers": 0,
        "batch_size": 128,
        "ubatch_size": 64,
        "extra_args": ["--jinja", "--reasoning", "off"],
    }

    cmd = local_llama_command(local, bridge, Path("llama-server"), Path("model.gguf"), Path("mmproj.gguf"))

    assert cmd[:2] == ["llama-server", "-m"]
    assert "-c" in cmd
    assert cmd[cmd.index("-c") + 1] == "512"
    assert "--mmproj" in cmd
    assert "--batch-size" in cmd
    assert "--ubatch-size" in cmd
    assert cmd[-3:] == ["--jinja", "--reasoning", "off"]
