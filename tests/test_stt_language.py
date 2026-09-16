from jarvis.voice.stt import resolve_stt_model


def test_stt_model_mapping_supports_english_and_hindi():
    assert resolve_stt_model("en-IN") == "vosk-model-small-en-us-0.15"
    assert resolve_stt_model("hi-IN") == "vosk-model-small-hi-0.22"


def test_stt_model_mapping_rejects_unknown_language():
    assert resolve_stt_model("fr-FR") is None
