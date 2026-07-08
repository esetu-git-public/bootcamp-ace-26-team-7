from streamlit.testing.v1 import AppTest


def test_landing_page_renders():
    at = AppTest.from_file("app.py")
    at.run()
    assert not at.exception


def test_title_displayed():
    at = AppTest.from_file("app.py")
    at.run()
    assert "Surface Crack Detection System" in at.markdown[0].value


def test_login_button_exists():
    at = AppTest.from_file("app.py")
    at.run()
    assert len(at.button) > 0
    assert at.button[0].label == "Login"
