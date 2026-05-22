from authsome.server import analytics


def test_init_posthog_respects_do_not_track(monkeypatch) -> None:
    monkeypatch.setenv("DO_NOT_TRACK", "1")

    analytics.shutdown_posthog()

    assert analytics.init_posthog() is None
    assert analytics.get_posthog() is None


def test_init_posthog_respects_posthog_disabled(monkeypatch) -> None:
    monkeypatch.setenv("POSTHOG_DISABLED", "1")

    analytics.shutdown_posthog()

    assert analytics.init_posthog() is None
    assert analytics.get_posthog() is None


def test_init_posthog_respects_authsome_analytics_override(monkeypatch) -> None:
    monkeypatch.setenv("AUTHSOME_ANALYTICS", "0")

    analytics.shutdown_posthog()

    assert analytics.init_posthog() is None
    assert analytics.get_posthog() is None


def test_init_posthog_initialises_client_when_opt_out_flags_are_unset(monkeypatch) -> None:
    class DummyPosthog:
        def __init__(self, api_key: str, *, host: str, enable_exception_autocapture: bool) -> None:
            self.api_key = api_key
            self.host = host
            self.enable_exception_autocapture = enable_exception_autocapture

        def shutdown(self) -> None:
            return None

    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    monkeypatch.delenv("POSTHOG_DISABLED", raising=False)
    monkeypatch.delenv("AUTHSOME_ANALYTICS", raising=False)
    monkeypatch.setattr(analytics, "Posthog", DummyPosthog)

    analytics.shutdown_posthog()
    client = analytics.init_posthog()

    assert isinstance(client, DummyPosthog)
    assert client.api_key == "phc_6HXMDi8CjfIW0l04l34L7IDkpCDeOVz9cOz1KLAHXh8"
    assert client.host == "https://us.i.posthog.com"
    assert client.enable_exception_autocapture is True

    analytics.shutdown_posthog()
