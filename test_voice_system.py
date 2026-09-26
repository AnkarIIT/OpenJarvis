import os
os.environ["JARVIS_HOME"] = "C:/Users/bamba/.jarvis"

print("=== Full wake word + voice system test ===")
try:
    from tools.wake_word import check_wake_word_requirements, load_wake_word_config
    from tools.voice_mode import check_voice_requirements
    
    # Wake word test
    print("\n--- Wake Word Requirements ---")
    wwkfg = load_wake_word_config()
    print(f"Wake word config: {wwkfg}")
    ww_reqs = check_wake_word_requirements(wwkfg)
    print(f"Wake word requirements: {ww_reqs}")
    print(f"AWAILABLE: {ww_reqs.get('available')}")
    
    # Voice mode test  
    print("\n--- Voice Mode Requirements ---")
    vr = check_voice_requirements()
    print(f"Voice requirements: {vr}")
    print(f"AUDIO AVAILABLE: {vr.get('audio_available')}")
    print(f"STT AVAILABLE: {vr.get('stt_available')}")
    
    # Summary
    print("\n=== SUMMARY ===")
    ww_ok = ww_reqs.get('available', False)
    vr_ok = vr.get('available', False)
    print(f"Wake Word: {'PASS' if ww_ok else 'FAIL'}")
    print(f"Voice Mode: {'PASS' if vr_ok else 'FAIL'}")
    
    if ww_ok and vr_ok:
        print("\nAll systems ready for hands-free voice!")
    else:
        print("\nSome systems need attention.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
