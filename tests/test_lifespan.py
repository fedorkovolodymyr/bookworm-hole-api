from unittest.mock import MagicMock

import pytest

from app.core.config import get_settings
from app.core.lifespan import _init_sentry


class TestInitSentry:
    def test_skips_init_when_dsn_unset(self, monkeypatch: pytest.MonkeyPatch):
        mock_init = MagicMock()
        monkeypatch.setattr("app.core.lifespan.sentry_sdk.init", mock_init)

        _init_sentry()

        mock_init.assert_not_called()

    def test_calls_init_when_dsn_set(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
        monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.5")
        monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")
        mock_init = MagicMock()
        monkeypatch.setattr("app.core.lifespan.sentry_sdk.init", mock_init)

        _init_sentry()

        mock_init.assert_called_once_with(
            dsn="https://example@sentry.io/1",
            environment=get_settings().app_settings.app_env,
            traces_sample_rate=0.5,
            profiles_sample_rate=0.1,
            send_default_pii=False,
        )
