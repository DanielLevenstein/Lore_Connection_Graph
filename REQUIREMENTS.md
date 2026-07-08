Create a local python app that allows users to chat with custom characters they create from short backstories.

The app must store all data locally and use an local instance of the model the project is configured to use.

agent memory files should be stored as .md files and chatlogs should be stored as raw text.
The model used in the app needs to be able to be switched out easily.
Each model config file should store the model URL, size of model and a one sentance description of it created from huggingface.

App should allow the user to select the model from a list of downloaded models.

Project File Structure:

* config/model_name.json (Model configurations)
* data/model_name
* data/characters/name/BACKSTORY.md
* data/characters/name/chatlogs/DATETIME_CHAT.log
* data/characters/name/MEMORY.md

A UI should be created to allow users to create new characters and chat with existing characters.

No files in data directory should be committed to source control.

Use `https://huggingface.co/DavidAU/L3.1-Evil-Reasoning-Dark-Planet-Hermes-R1-Uncensored-8B` as the first initial model.
