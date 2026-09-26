import os
os.environ["JARVIS_HOME"] = "C:/Users/bamba/.jarvis"

print("=== Testing Jarvis TTS requirements ===")
try:
    from tools.tts_tool import check_tts_requirements, _load_tts_config, _get_provider
    tts_config = _load_tts_config()
    print(f"TTS config: {tts_config}")
    provider = _get_provider(tts_config)
    print(f"Provider: {provider}")
    result = check_tts_requirements()
    print(f"check_tts_requirements result: {result}")
    print(f"Type: {type(result)}")
    if isinstance(result, dict):
        print(f"Success: {result.get('success')}")
    elif isinstance(result, str):
        import json
        parsed = json.loads(result)
        print(f"Success: {parsed.get('success')}")
        print(f"Error: {parsed.get('error')}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
