from streamlit.testing.v1 import AppTest


def _fill_valid_form(at):
    at.text_input[0].set_value("Test User")
    at.text_input[1].set_value("test@example.com")
    at.text_input[2].set_value("1234567890")
    at.text_input[3].set_value("Test@1234")
    at.text_input[4].set_value("Test@1234")
    return at


def test_form_renders():
    at = AppTest.from_file("pages/register.py")
    at.run()
    assert not at.exception
    labels = {t.label for t in at.text_input}
    assert labels == {"Full Name", "Email", "Phone Number", "Password", "Confirm Password"}
    assert any(b.label == "Create Account" for b in at.button)


def test_success_message():
    at = AppTest.from_file("pages/register.py")
    at.run()
    _fill_valid_form(at)
    at.button[0].click().run()
    assert any("Registration successful" in s.value for s in at.success)


def test_success_shows_verify_email_info():
    at = AppTest.from_file("pages/register.py")
    at.run()
    _fill_valid_form(at)
    at.button[0].click().run()
    assert any("verify your account" in i.value.lower() for i in at.info)


def test_password_mismatch():
    at = AppTest.from_file("pages/register.py")
    at.run()
    at.text_input[0].set_value("Test User")
    at.text_input[1].set_value("test@example.com")
    at.text_input[2].set_value("1234567890")
    at.text_input[3].set_value("Pass1234")
    at.text_input[4].set_value("DifferentPass")
    at.button[0].click().run()
    assert any("do not match" in e.value.lower() for e in at.error)


def test_short_password():
    at = AppTest.from_file("pages/register.py")
    at.run()
    at.text_input[0].set_value("Test User")
    at.text_input[1].set_value("test@example.com")
    at.text_input[2].set_value("1234567890")
    at.text_input[3].set_value("Ab1")
    at.text_input[4].set_value("Ab1")
    at.button[0].click().run()
    assert any("at least 6" in e.value.lower() for e in at.error)


def test_empty_required_fields():
    at = AppTest.from_file("pages/register.py")
    at.run()
    at.button[0].click().run()
    assert any("fill in all" in e.value.lower() for e in at.error)


def test_back_to_login_button():
    at = AppTest.from_file("pages/register.py")
    at.run()
    assert any(b.label == "⬅ Back to Login" for b in at.button)
