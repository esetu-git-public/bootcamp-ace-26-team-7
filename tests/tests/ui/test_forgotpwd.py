from streamlit.testing.v1 import AppTest


def test_form_renders():
    at = AppTest.from_file("pages/forgotpwd.py")
    at.run()
    assert not at.exception
    assert any(t.label == "Email Address" for t in at.text_input)
    assert any(b.label == "Send Reset Link" for b in at.button)


def test_valid_email_shows_success():
    at = AppTest.from_file("pages/forgotpwd.py")
    at.run()
    at.text_input[0].set_value("admin@surfacedetect.com")
    at.button[0].click().run()
    assert any("reset link" in s.value.lower() for s in at.success)


def test_empty_email_shows_error():
    at = AppTest.from_file("pages/forgotpwd.py")
    at.run()
    at.button[0].click().run()
    assert any("email address" in e.value.lower() for e in at.error)


def test_back_to_login_button():
    at = AppTest.from_file("pages/forgotpwd.py")
    at.run()
    assert any(b.label == "⬅ Back to Login" for b in at.button)
