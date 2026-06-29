from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".codex-hybrid-model-switcher" / "config.json"


def expand_path(value: str | os.PathLike[str]) -> Path:
    text = os.path.expandvars(str(value))
    text = os.path.expanduser(text)
    return Path(text)


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    port: int
    llama_port: int
    idle_seconds: int


@dataclass(frozen=True)
class AppConfig:
    path: Path
    raw: dict[str, Any]

    @property
    def codex_home(self) -> Path:
        return expand_path(self.raw.get("codex_home") or "~/.codex")

    @property
    def cc_switch_home(self) -> Path:
        return expand_path(self.raw.get("cc_switch_home") or "~/.cc-switch")

    @property
    def bridge(self) -> BridgeConfig:
        data = self.raw.get("bridge") or {}
        return BridgeConfig(
            host=str(data.get("host") or "127.0.0.1"),
            port=int(data.get("port") or 19030),
            llama_port=int(data.get("llama_port") or 19031),
            idle_seconds=int(data.get("idle_seconds") or 600),
        )

    @property
    def providers(self) -> list[dict[str, Any]]:
        return [p for p in self.raw.get("providers", []) if isinstance(p, dict) and p.get("id")]

    @property
    def local_model(self) -> dict[str, Any]:
        model = self.raw.get("local_model") or {}
        if not isinstance(model, dict):
            raise ValueError("local_model must be an object")
        return model

    def provider(self, provider_id: str) -> dict[str, Any]:
        for provider in self.providers:
            if provider.get("id") == provider_id:
                return provider
        raise KeyError(f"unknown provider id: {provider_id}")

    def provider_for_model(self, model: str) -> dict[str, Any] | None:
        local_id = str(self.local_model.get("id") or "local/gemma")
        if model == local_id:
            return {"kind": "local", "model": local_id}
        for provider in self.providers:
            if provider.get("model") == model:
                return provider
        return None


def load_config(path: str | None = None) -> AppConfig:
    config_path = expand_path(path or os.environ.get("CODEX_HYBRID_CONFIG") or DEFAULT_CONFIG)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"config must be a JSON object: {config_path}")
    return AppConfig(config_path, data)

