from streamlit.testing.v1 import AppTest


def test_form_renders():
    at = AppTest.from_file("pages/login.py")
    at.run()
    assert not at.exception
    assert any(t.label == "Email" for t in at.text_input)
    assert any(t.label == "Password" for t in at.text_input)
    assert any(b.label == "Login" for b in at.button)


def test_success_sets_session_state():
    at = AppTest.from_file("pages/login.py")
    at.run()
    at.text_input[0].set_value("admin@surfacedetect.com")
    at.text_input[1].set_value("Admin@123").run()
    assert at.session_state["access_token"] == "hardcoded-admin-token"
    assert at.session_state["user"]["email"] == "admin@surfacedetect.com"


def test_failure_shows_error():
    at = AppTest.from_file("pages/login.py")
    at.run()
    at.text_input[0].set_value("wrong@email.com")
    at.text_input[1].set_value("WrongPass123").run()
    assert at.session_state.get("access_token") is None
    assert any("Invalid" in e.value for e in at.error)


def test_empty_fields_shows_error():
    at = AppTest.from_file("pages/login.py")
    at.run()
    at.button[0].click().run()
    assert at.session_state.get("access_token") is None
    assert any(
        "Please enter both" in e.value for e in at.error
    )


def test_forgot_password_button_navigates():
    at = AppTest.from_file("pages/login.py")
    at.run()
    assert any(
        b.label == "Forgot Password" for b in at.button
    )


def test_register_button_exists():
    at = AppTest.from_file("pages/login.py")
    at.run()
    assert any(b.label == "Register" for b in at.button)
