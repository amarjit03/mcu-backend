from app.core.config import settings


def test_settings_loading() -> None:
    """
    Asserts that environment configurations load correctly with valid defaults.
    """
    assert settings.PROJECT_NAME == "Student Complaint Management System"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.RATE_LIMIT_PER_MINUTE == 100
