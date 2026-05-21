import pytest
import django
from rest_framework.test import APIClient

def pytest_configure():
    """
    Forces django initialization sequentially during the pytest startup process
    before any test collection begins.
    """
    django.setup()

@pytest.fixture
def api_client():
    return APIClient()
