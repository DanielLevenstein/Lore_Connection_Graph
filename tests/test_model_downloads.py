import os
from pathlib import Path

import language_model_harness
from model_harness import environment
from model_harness.downloads import default_download_option, downloaded_options
from model_harness.models import ModelConfig, list_model_configs
from character_graph.extraction import extract_character_graph
from character_graph.ingest import load_backstory
from language_model_harness import configure_language_model_harness


def test_default_download_option_skips_mmproj_projector():
    config = model_config(
        [
            {"quant": "default", "filename": "mmproj-model-bf16.gguf", "size": "0.92 GB"},
            {"quant": "Q4_K", "filename": "model-Q4_K.gguf", "size": "5.78 GB"},
            {"quant": "default", "filename": "model-bf16.gguf", "size": "18.41 GB"},
        ]
    )

    assert default_download_option(config)["filename"] == "model-Q4_K.gguf"


def test_downloaded_options_only_returns_runnable_model_files(tmp_path):
    config = model_config(
        [
            {"quant": "default", "filename": "mmproj-model-bf16.gguf", "size": "0.92 GB"},
            {"quant": "Q4_K", "filename": "model-Q4_K.gguf", "size": "5.78 GB"},
        ],
        local_dir=tmp_path,
    )
    (tmp_path / "mmproj-model-bf16.gguf").write_text("projector", encoding="utf-8")
    (tmp_path / "model-Q4_K.gguf").write_text("model", encoding="utf-8")

    assert [option["filename"] for option in downloaded_options(config)] == ["model-Q4_K.gguf"]


def test_selected_semantic_model_config_is_runnable_gguf():
    configure_language_model_harness()

    configs = {config.name: config for config in list_model_configs()}
    semantic = configs["qwen2.5-3b-instruct-gguf"]

    assert semantic.server["runner"] == "llama.cpp"
    assert "semantic model" in semantic.description.lower()
    assert default_download_option(semantic)["filename"] == "Qwen2.5-3B-Instruct-IQ2_M.gguf"


def test_selected_visual_inspection_model_config_is_available():
    configure_language_model_harness()

    configs = {config.name: config for config in list_model_configs()}
    visual = configs["qwen2.5-vl-3b-instruct"]

    assert visual.model_id == "Qwen/Qwen2.5-VL-3B-Instruct"
    assert visual.server["runner"] == "vLLM"
    assert "visual inspection model" in visual.description.lower()


def test_model_harness_data_defaults_under_world_building(monkeypatch):
    monkeypatch.delenv(environment.DATA_DIR_ENV, raising=False)

    assert environment.data_dir() == environment.DEFAULT_PROJECT_DIR / "world_building" / "meta_data" / "model"


def test_language_model_harness_configures_model_data_under_world_building(monkeypatch):
    monkeypatch.delenv(environment.DATA_DIR_ENV, raising=False)

    language_model_harness.configure_language_model_harness()

    assert (
        Path(os.environ[environment.DATA_DIR_ENV])
        == language_model_harness.ROOT_DIR / "world_building" / "meta_data" / "model"
    )


def test_semantic_extraction_finds_people_and_places_in_fixture_lore():
    graph = extract_character_graph(
        load_backstory(
            Path("tests/fixtures/character_sheets/Orin_Nightbloom.md"),
            character_id="Orin_Nightbloom",
        )
    )

    people = {character.name for character in graph.characters.values()}
    places = {place.name for place in graph.places.values()}

    assert "Orin Nightbloom" in people
    assert "Orin Nightbloom's Mother" in people
    assert "Sunstone Mage College" in places


def model_config(download_options: list[dict], local_dir: Path | None = None) -> ModelConfig:
    config = ModelConfig(
        name="test-model",
        model_id="org/test-model",
        model_url="https://example.test/org/test-model",
        api_base_url="http://127.0.0.1:8000/v1",
        size="9B",
        download_size="default 0.92 GB",
        download_options=download_options,
        description="test",
        server={},
        config_path=Path("config/test-model.json"),
    )
    if local_dir is None:
        return config
    return LocalDirModelConfig(config, local_dir)


class LocalDirModelConfig(ModelConfig):
    def __init__(self, config: ModelConfig, local_dir: Path) -> None:
        object.__setattr__(self, "name", config.name)
        object.__setattr__(self, "model_id", config.model_id)
        object.__setattr__(self, "model_url", config.model_url)
        object.__setattr__(self, "api_base_url", config.api_base_url)
        object.__setattr__(self, "size", config.size)
        object.__setattr__(self, "download_size", config.download_size)
        object.__setattr__(self, "download_options", config.download_options)
        object.__setattr__(self, "description", config.description)
        object.__setattr__(self, "server", config.server)
        object.__setattr__(self, "config_path", config.config_path)
        object.__setattr__(self, "_local_dir", local_dir)

    @property
    def local_dir(self) -> Path:
        return self._local_dir
