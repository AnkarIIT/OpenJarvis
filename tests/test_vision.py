from jarvis.utils.vision import build_vision_report, supported_document


def test_vision_report_has_explicit_multimodal_boundary():
    report = build_vision_report()
    assert "camera_analysis" in report
    assert report["llm_multimodal_input"] is False


def test_supported_document_extensions():
    assert supported_document("report.pdf")
    assert supported_document("notes.md")
    assert not supported_document("archive.zip")
