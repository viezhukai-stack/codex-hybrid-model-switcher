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
class HotRouterConfig:
    host: str
    port: int
    default_cloud_provider_id: str | None
    hidden_model_ids: tuple[str, ...]
    visible_model_ids: tuple[str, ...]
    model_aliases: dict[str, str]
    catalog_cache_seconds: float


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
    def hot_router(self) -> HotRouterConfig:
        data = self.raw.get("hot_router") or {}
        if not isinstance(data, dict):
            raise ValueError("hot_router must be an object")

        def string_tuple(key: str) -> tuple[str, ...]:
            values = data.get(key) or []
            if not isinstance(values, list):
                return ()
            return tuple(value for value in values if isinstance(value, str) and value)

        aliases = data.get("model_aliases") or {}
        if not isinstance(aliases, dict):
            aliases = {}
        return HotRouterConfig(
            host=str(data.get("host") or "127.0.0.1"),
            port=int(data.get("port") or 19032),
            default_cloud_provider_id=(
                str(data["default_cloud_provider_id"])
                if data.get("default_cloud_provider_id")
                else None
            ),
            hidden_model_ids=string_tuple("hidden_model_ids"),
            visible_model_ids=string_tuple("visible_model_ids"),
            model_aliases={
                str(key): str(value)
                for key, value in aliases.items()
                if isinstance(key, str) and key and isinstance(value, str) and value
            },
            catalog_cache_seconds=float(data.get("catalog_cache_seconds") or 15),
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

    @property
    def account_switch(self) -> dict[str, Any]:
        data = self.raw.get("account_switch") or {}
        if not isinstance(data, dict):
            raise ValueError("account_switch must be an object")
        return data

    def provider(self, provider_id: str) -> dict[str, Any]:
        for provider in self.providers:
            if provider.get("id") == provider_id:
                return provider
        raise KeyError(f"unknown provider id: {provider_id}")

    def provider_for_model(self, model: str) -> dict[str, Any] | None:
        local_id = str(self.local_model.get("id") or "local/gemma")
        local_providers = [provider for provider in self.providers if provider.get("kind") == "local"]
        if model == local_id and local_providers:
            return {"kind": "local", "model": local_id}
        bridge_clouds = [
            provider
            for provider in self.providers
            if provider.get("kind") == "cloud" and str(provider.get("route") or "direct") == "bridge"
        ]
        for provider in self.providers:
            if provider.get("model") != model:
                continue
            if provider.get("kind") == "official" and len(bridge_clouds) == 1:
                proxied = dict(bridge_clouds[0])
                proxied["model"] = model
                return proxied
            if provider.get("kind") != "official":
                return provider
        if len(bridge_clouds) == 1 and (model.startswith("gpt-") or model.startswith("codex-")):
            proxied = dict(bridge_clouds[0])
            proxied["model"] = model
            return proxied
        return None


def load_config(path: str | None = None) -> AppConfig:
    config_path = expand_path(path or os.environ.get("CODEX_HYBRID_CONFIG") or DEFAULT_CONFIG)
    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"config must be a JSON object: {config_path}")
    return AppConfig(config_path, data)
