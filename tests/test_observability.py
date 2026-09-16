from jarvis.agent.llm_client import LLMClient
from jarvis.config.settings import Settings


def test_llm_observability_defaults():
    state = LLMClient(Settings()).observability
    assert state["active_provider"] is None
    assert state["attempts"] == 0
    assert state["fallbacks"] == 0
