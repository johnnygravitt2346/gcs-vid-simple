#!/usr/bin/env python3
"""
Asset resolver for named slots with preflight validation.

Resolves asset slots to concrete URIs, allowing values to be either
gs:// URIs or relative names within the channel assets folder.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

try:
    from .cloud_storage import get_cloud_storage
    from .path_resolver import get_path_resolver_for_channel
    from .channel_config import ASSET_SLOTS, ChannelConfig, load_channel_config
except ImportError:
    from cloud_storage import get_cloud_storage
    from path_resolver import get_path_resolver_for_channel
    from channel_config import ASSET_SLOTS, ChannelConfig, load_channel_config


class AssetResolver:
    """Resolve asset slots for a channel and validate presence in GCS."""

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.storage = get_cloud_storage()
        self.resolver = get_path_resolver_for_channel(channel_id)
        self.config = load_channel_config(channel_id)

    def _resolve_ref(self, ref: str) -> str:
        """Resolve a single asset reference to a GCS URI."""
        if ref.startswith("gs://"):
            return ref
        # Treat as relative to the channel assets folder
        return f"{self.resolver.assets_uri()}/{ref}"

    def resolve_all(self) -> Dict[str, str]:
        """Resolve all slots to GCS URIs."""
        resolved: Dict[str, str] = {}
        for slot in ASSET_SLOTS:
            ref = self.config.assets.get(slot)
            if not ref:
                continue
            resolved[slot] = self._resolve_ref(ref)
        return resolved

    def preflight_validate(self) -> Tuple[bool, Dict[str, str]]:
        """Validate that all required slots exist. Return (ok, errors_by_slot)."""
        resolved = self.resolve_all()
        errors: Dict[str, str] = {}
        for slot in ASSET_SLOTS:
            uri = resolved.get(slot)
            if not uri:
                errors[slot] = "Missing reference in config"
                continue
            if not self.storage.blob_exists(uri):
                errors[slot] = f"Asset not found: {uri}"
        return (len(errors) == 0), errors


