from pathlib import Path

from model_harness.downloads import default_download_option, downloaded_options
from model_harness.models import ModelConfig


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
