from pathlib import Path

from streamlit.testing.v1 import AppTest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_page_renders():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert not at.exception
    assert any("Surface Crack Detection" in m.value for m in at.markdown)


def test_sidebar_radio_exists():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    radio = at.sidebar.radio
    assert len(radio) > 0
    assert radio[0].label == "Select Class"


def test_sidebar_radio_default():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert at.sidebar.radio[0].value == "POTHOLES"


def test_sidebar_radio_change_class():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    at.sidebar.radio[0].set_value("CRACK").run()
    assert at.sidebar.radio[0].value == "CRACK"


def test_file_uploader_exists():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert len(at.file_uploader) > 0


def test_upload_file_displays_image():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path).run()
    assert len(at.image) > 0


def test_data_processed_section():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert any("Data Processed" in h.value for h in at.header)


def test_severity_info_before_prediction():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert any("Upload an image and run" in i.value for i in at.info)


def test_prediction_upload_and_run(mock_model_fallback):
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path)
    at.button[0].click().run()
    assert any("Potholes" in s.value for s in at.success)


def test_prediction_shows_confidence(mock_model_fallback):
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path)
    at.button[0].click().run()
    assert any(
        "85.0%" in m.value or "85.0 %" in m.value
        for m in at.metric
    )


def test_prediction_shows_progress_bars(mock_model_fallback):
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path)
    at.button[0].click().run()
    assert len(at.progress) > 0


def test_prediction_shows_severity(mock_model_fallback):
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path)
    at.button[0].click().run()
    assert any("High" in m.value for m in at.markdown)


def test_prediction_shows_report(mock_model_fallback):
    at = AppTest.from_file("pages/Home.py")
    at.run()
    sample_path = str(FIXTURES_DIR / "sample.jpg")
    at.file_uploader[0].upload(sample_path)
    at.button[0].click().run()
    assert any("Potholes" in t.value for t in at.text_area)


def test_download_button_exists():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    assert any(b.label == "Download Report" for b in at.download_button)


def test_prediction_without_upload():
    at = AppTest.from_file("pages/Home.py")
    at.run()
    at.button[0].click().run()
    assert not any("error" in str(e.value).lower() for e in at.error)
