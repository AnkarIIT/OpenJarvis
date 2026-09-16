from jarvis.config.settings import Settings
from jarvis.utils.health import build_health_report


def test_health_report_has_operational_sections():
    report = build_health_report(Settings())
    assert report["runtime"]["supported_python"] is True
    assert "dependencies" in report
    assert "providers" in report
    assert "mcp" in report
    assert report["mcp"]["dangerous_enabled"] is False
