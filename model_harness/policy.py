EXTERNAL_LANGUAGE_MODEL_ERROR = (
    "External language-model use is disabled for this release. "
    "Only codebase-owned deterministic generation is allowed."
)


def require_codebase_owned_language_model() -> None:
    raise RuntimeError(EXTERNAL_LANGUAGE_MODEL_ERROR)
