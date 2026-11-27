import pytest
from unittest.mock import patch

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def fake_frontend(hass):
    """The test environment has no frontend build: count it as loaded and record the card URL."""
    hass.config.components.add("frontend")
    with patch("custom_components.home_flow_explorer.add_extra_js_url") as add_js:
        hass.data["hfe_test_js"] = add_js
        yield add_js
