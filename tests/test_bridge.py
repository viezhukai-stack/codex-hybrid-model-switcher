from __future__ import annotations

from codex_hybrid_switcher.bridge import (
    chat_parts_from_content,
    clean_local_text,
    image_url_from_part,
    responses_input_to_messages,
)


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
