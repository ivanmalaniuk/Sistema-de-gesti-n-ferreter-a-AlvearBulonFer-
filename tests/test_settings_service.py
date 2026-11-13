import pytest
from decimal import Decimal
from unittest.mock import create_autospec

from src.domain.interfaces import ISettingsRepository
from src.application.settings_service import SettingsService


@pytest.fixture
def settings_repo():
    repo = create_autospec(ISettingsRepository)
    repo.get.side_effect = lambda k, d="": {
        "usd_rate": "120.50",
        "profit_margin": "160",
    }.get(k, d)
    return repo


@pytest.fixture
def settings_service(settings_repo):
    return SettingsService(settings_repo)


class TestSettingsService:
    def test_get_usd_rate(self, settings_service):
        assert settings_service.get_usd_rate() == Decimal("120.50")

    def test_set_usd_rate(self, settings_service, settings_repo):
        settings_service.set_usd_rate(Decimal("200"))
        settings_repo.set.assert_called_once_with("usd_rate", "200")

    def test_set_invalid_rate_raises_error(self, settings_service, settings_repo):
        with pytest.raises(ValueError, match="mayor a cero"):
            settings_service.set_usd_rate(Decimal("0"))

    def test_get_profit_margin(self, settings_service):
        assert settings_service.get_profit_margin() == Decimal("160")

    def test_set_profit_margin(self, settings_service, settings_repo):
        settings_service.set_profit_margin(Decimal("150"))
        settings_repo.set.assert_called_once_with("profit_margin", "150")
