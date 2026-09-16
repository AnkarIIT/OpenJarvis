from jarvis.agent.system_prompt import get_system_prompt


def test_prompt_matches_user_language_when_auto_detection_enabled():
    prompt = get_system_prompt(language="en-IN", language_detection=True)
    assert "same language" in prompt
    assert "Do not translate" in prompt


def test_prompt_supports_fixed_language():
    prompt = get_system_prompt(language="hi-IN", language_detection=False)
    assert "Reply in hi-IN" in prompt
