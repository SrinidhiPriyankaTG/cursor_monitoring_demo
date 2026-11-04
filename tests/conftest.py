import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "test.db"
    application = create_app(
        {
            "TESTING": True,
            "DATABASE": str(database),
            "SECRET_KEY": "test-secret",
        }
    )
    return application


@pytest.fixture
def client(app):
    return app.test_client()

