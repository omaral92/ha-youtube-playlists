"""Tests for registering the Lovelace card as a resource (not add_extra_js_url).

See _async_register_lovelace_resource in __init__.py: add_extra_js_url()
races the frontend's custom-element registry shim, causing an intermittent
"Custom element doesn't exist" error. Resources are loaded after the shim is
in place, so we prefer them and only fall back to add_extra_js_url when
resource storage isn't available (YAML mode / Lovelace not set up / error).
"""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.youtube_playlists import _async_register_lovelace_resource

CARD_URL = "/youtube_playlists_files/youtube-playlist-card.js?v=1.5.5"


class FakeResourceStorageCollection:
    """Stand-in for homeassistant.components.lovelace.resources.ResourceStorageCollection."""

    def __init__(self, items=None, fail_create: bool = False):
        self._items = list(items or [])
        self._fail_create = fail_create
        self.get_info_called = False
        self.created: list[dict] = []

    async def async_get_info(self):
        self.get_info_called = True
        return {"resources": len(self._items)}

    def async_items(self):
        return self._items

    async def async_create_item(self, data: dict):
        if self._fail_create:
            raise RuntimeError("storage write failed")
        item = {**data, "id": f"id{len(self._items) + 1}"}
        self._items.append(item)
        self.created.append(item)
        return item


def _install_fake_resources_module(cls: type) -> None:
    """Make `from homeassistant.components.lovelace.resources import
    ResourceStorageCollection` resolve to our fake, and nothing else be a
    ResourceStorageCollection (so YAML-mode collections correctly fail the
    isinstance check).
    """
    mod = types.ModuleType("homeassistant.components.lovelace.resources")
    mod.ResourceStorageCollection = cls
    sys.modules["homeassistant.components.lovelace.resources"] = mod


@pytest.mark.asyncio
async def test_registers_resource_when_absent(monkeypatch) -> None:
    _install_fake_resources_module(FakeResourceStorageCollection)
    collection = FakeResourceStorageCollection(items=[])
    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(resources=collection)}

    result = await _async_register_lovelace_resource(hass, CARD_URL)

    assert result is True
    assert collection.get_info_called  # forced a load before reading items
    assert len(collection.created) == 1
    assert collection.created[0]["res_type"] == "module"
    assert collection.created[0]["url"] == CARD_URL


@pytest.mark.asyncio
async def test_no_duplicate_when_already_registered(monkeypatch) -> None:
    """A previous install's resource (even with a different ?v=) is left alone."""
    _install_fake_resources_module(FakeResourceStorageCollection)
    existing = [{"id": "id1", "res_type": "module", "url": CARD_URL.split("?")[0] + "?v=1.4.0"}]
    collection = FakeResourceStorageCollection(items=existing)
    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(resources=collection)}

    result = await _async_register_lovelace_resource(hass, CARD_URL)

    assert result is True
    assert collection.created == []  # nothing new created
    assert collection.async_items() == existing  # untouched


@pytest.mark.asyncio
async def test_falls_back_when_yaml_mode(monkeypatch) -> None:
    """YAML-mode collections have no async_create_item; must not be treated as storage."""
    _install_fake_resources_module(FakeResourceStorageCollection)

    class FakeYamlCollection:
        async def async_get_info(self):
            return {"resources": 0}

        def async_items(self):
            return []

    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(resources=FakeYamlCollection())}

    result = await _async_register_lovelace_resource(hass, CARD_URL)

    assert result is False  # caller should fall back to add_extra_js_url


@pytest.mark.asyncio
async def test_falls_back_when_lovelace_not_set_up(monkeypatch) -> None:
    _install_fake_resources_module(FakeResourceStorageCollection)
    hass = MagicMock()
    hass.data = {}

    result = await _async_register_lovelace_resource(hass, CARD_URL)

    assert result is False


@pytest.mark.asyncio
async def test_falls_back_on_unexpected_error(monkeypatch) -> None:
    """A storage error must not break integration setup - just fall back."""
    _install_fake_resources_module(FakeResourceStorageCollection)
    collection = FakeResourceStorageCollection(items=[], fail_create=True)
    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(resources=collection)}

    result = await _async_register_lovelace_resource(hass, CARD_URL)

    assert result is False
