"""state.py のユニットテスト。"""

import json
import pytest
from pathlib import Path
from src.state import load, save, needs_update


@pytest.fixture
def tmp_state(tmp_path):
    return tmp_path / "state.json"


def test_load_returns_empty_when_no_file(tmp_state):
    assert load(tmp_state) == {}


def test_save_and_load_roundtrip(tmp_state):
    data = {"file1": "2026-06-01T00:00:00Z", "file2": "2026-06-02T00:00:00Z"}
    save(data, tmp_state)
    assert load(tmp_state) == data


def test_needs_update_when_new_file():
    f = {"id": "file1", "modifiedTime": "2026-06-01T00:00:00Z"}
    assert needs_update(f, {}) is True


def test_needs_update_when_modified():
    f = {"id": "file1", "modifiedTime": "2026-06-02T00:00:00Z"}
    state = {"file1": "2026-06-01T00:00:00Z"}
    assert needs_update(f, state) is True


def test_no_update_when_unchanged():
    f = {"id": "file1", "modifiedTime": "2026-06-01T00:00:00Z"}
    state = {"file1": "2026-06-01T00:00:00Z"}
    assert needs_update(f, state) is False
