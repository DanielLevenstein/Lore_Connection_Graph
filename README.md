# Dark Chatbot Local

A local Streamlit app for creating custom chat characters from short backstories and chatting with them through a local OpenAI-compatible model server.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Model Server

This app requires a local installation of llama will set up a API endpoint and download your chosen model locally through the configuration in the app side panel.

Mac Install:

`brew install llama.cpp`

Windows Install:

https://llama-cpp.com/download/


### Manually Starting Server

The app expects a local OpenAI-compatible chat completions endpoint. The initial config points at:

```text
http://localhost:8000/v1
```

For the included Hugging Face GGUF model, the generated JSON stores a llama.cpp startup command:

```bash
llama serve -hf DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF:Q4_K_M
```

Start it from the config file:

```bash
.venv/bin/python scripts/start_model_server.py \
  config/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF.json \
  --wait 10
```

You can also start and stop the configured server from the app sidebar after marking the model as downloaded.

Model configs live in `config/*.json`. Add another JSON file there to make a new model selectable. A model is considered downloaded when its matching `data/<model_name>/` folder exists; the app can create that local folder from the Models panel.

For GGUF configs, use the app sidebar to pick a quant and download the selected file into:

```text
data/<model_name>/<filename>.gguf
```

The downloaded-model selector only shows GGUF models after one of their files exists locally. Starting the server then uses the local file instead of the Hugging Face page.

Generate a config from a Hugging Face model URL or repo ID:

```bash
.venv/bin/python scripts/generate_model_config.py "owner/model-name"
```

For GGUF repos with multiple quants, the generator picks `Q4_K_M` by default when available and stores all `.gguf` file sizes in `download_options`. Choose a different default quant with:

```bash
.venv/bin/python scripts/generate_model_config.py \
  "owner/model-name" \
  --quant Q5_K_M
```

The generator also writes a `server.command` list. GGUF repos default to `llama serve -hf ...`, while non-GGUF repos default to `vllm serve ...`.

Download a configured artifact from the command line:

```bash
.venv/bin/python scripts/download_model.py \
  config/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF.json
```

Or choose a specific file:

```bash
.venv/bin/python scripts/download_model.py \
  config/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF.json \
  --filename Gemma-The-Writer-N-Restless-Quill-10B-D_AU-Q4_k_m.gguf
```

## Local Data Layout

The app creates and reads:

```text
config/model_name.json
data/model_name
data/characters/name/BACKSTORY.md
data/characters/name/MEMORY.md
data/characters/name/chatlogs/DATETIME_CHAT.log
```

Everything under `data/` is ignored by git.
