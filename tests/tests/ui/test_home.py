from pathlib import Path

from streamlit.testing.v1 import AppTest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _logged_in_at():
    at = AppTest.from_file("pages/home.py")
    at.session_state["access_token"] = "hardcoded-admin-token"
    at.session_state["user"] = {"email": "admin@surfacedetect.com", "full_name": "Admin"}
    return at


def test_page_renders():
    at = _logged_in_at()
    at.run()
    assert not at.exception
    assert any("Surface Crack Detection" in m.value for m in at.markdown)


def test_sidebar_radio_exists():
    at = _logged_in_at()
    at.run()
    radio = at.sidebar.radio
    assert len(radio) > 0
    assert radio[0].label == "Select Class"


def test_sidebar_radio_default():
    at = _logged_in_at()
    at.run()
    assert at.sidebar.radio[0].value == "POTHOLES"


def test_sidebar_radio_change_class():
    at = _logged_in_at()
    at.run()
    at.sidebar.radio[0].set_value("CRACK").run()
    assert at.sidebar.radio[0].value == "CRACK"


def test_severity_info_before_prediction():
    at = _logged_in_at()
    at.run()
    assert any("Upload an image and run" in i.value for i in at.info)


def test_prediction_without_upload():
    at = _logged_in_at()
    at.run()
    at.button[0].click().run()
    assert not any("error" in str(e.value).lower() for e in at.error)
