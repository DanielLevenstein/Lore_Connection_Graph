import pytest

import local_chatbot.storage as storage


@pytest.fixture(autouse=True)
def isolate_generated_graph_json(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "CHARACTER_GRAPHS_DIR", tmp_path / "data" / "character_graph")
