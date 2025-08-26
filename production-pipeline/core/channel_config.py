#!/usr/bin/env python3
"""
Channel configuration model and helpers.

Defines the named-slot asset model for a channel and provides
load/save utilities against the channel config GCS location.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

try:
    from .cloud_storage import get_cloud_storage
    from .path_resolver import get_path_resolver_for_channel
except ImportError:
    from cloud_storage import get_cloud_storage
    from path_resolver import get_path_resolver_for_channel


ASSET_SLOTS = [
    "TEMPLATE_1",
    "TEMPLATE_2",
    "TEMPLATE_3",
    "TIMER_VIDEO",
    "TIMER_PNG",
    "TICKING_AUDIO",
    "DING_AUDIO",
]


@dataclass
class FeedDefaults:
    mode: str = "gemini"  # gemini | csv
    tts_voice: str = "en-US-Neural2-F"
    tts_speed: float = 1.0


@dataclass
class RenderDefaults:
    fps: int = 30
    resolution: str = "1920x1080"
    pause_after_seconds: float = 5.0


@dataclass
class ChannelConfig:
    name: str
    type: str = "trivia"
    # Map slot name -> asset reference (either gs://... or relative name within channel assets)
    assets: Dict[str, str] = field(default_factory=dict)
    feed_defaults: FeedDefaults = field(default_factory=FeedDefaults)
    render_defaults: RenderDefaults = field(default_factory=RenderDefaults)

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(data: Dict) -> ChannelConfig:
        return ChannelConfig(
            name=data.get("name", "unknown"),
            type=data.get("type", "trivia"),
            assets=data.get("assets", {}),
            feed_defaults=FeedDefaults(**data.get("feed_defaults", {})),
            render_defaults=RenderDefaults(**data.get("render_defaults", {})),
        )


def load_channel_config(channel_id: str) -> ChannelConfig:
    """Load channel config from GCS, auto-provision if missing with sane defaults."""
    resolver = get_path_resolver_for_channel(channel_id)
    storage = get_cloud_storage()
    cfg_uri = resolver.channel_config_uri()

    # Auto-provision default config if not present
    if not storage.blob_exists(cfg_uri):
        config = default_channel_config(channel_id)
        storage.write_text_to_gcs(json.dumps(config.to_dict(), indent=2), cfg_uri, f"channel_config_provision_{channel_id}")
        return config

    data = storage.read_json_from_gcs(cfg_uri, f"channel_config_read_{channel_id}")
    return ChannelConfig.from_dict(data)


def save_channel_config(channel_id: str, config: ChannelConfig) -> str:
    """Persist channel config to its GCS location."""
    resolver = get_path_resolver_for_channel(channel_id)
    storage = get_cloud_storage()
    cfg_uri = resolver.channel_config_uri()
    storage.write_text_to_gcs(json.dumps(config.to_dict(), indent=2), cfg_uri, f"channel_config_write_{channel_id}")
    return cfg_uri


def default_channel_config(channel_id: str) -> ChannelConfig:
    """Return a working default config for a channel (uses the shared test assets)."""
    # Defaults point to shared asset pack; these exist in 'trivia-automations-2/channel-test/video-assets/'
    # This matches the existing asset location in the project memory and current generators.
    assets = {
        "TEMPLATE_1": "1.mp4",
        "TEMPLATE_2": "2.mp4",
        "TEMPLATE_3": "3.mp4",
        "TIMER_VIDEO": "slide_timer_bar_5s.mp4",
        "TIMER_PNG": "slide_timer_bar_full_striped.png",
        "TICKING_AUDIO": "ticking_clock_mechanical_5s.wav",
        "DING_AUDIO": "ding_correct_answer_long.wav",
    }
    return ChannelConfig(name=channel_id, assets=assets)


