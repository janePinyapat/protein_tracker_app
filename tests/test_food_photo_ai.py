"""Tests for the AI photo-analysis client.

Every test injects a stub Anthropic client, so the suite never makes a real
API call, never needs a real key, and never spends money.
"""

import anthropic
import pytest

from food_photo_ai import (
    FoodPhotoError,
    MAX_PHOTO_BYTES,
    PhotoAnalysis,
    analyze_food_photo,
    get_api_key,
)


class StubMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.last_kwargs = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error:
            raise self.error
        return self.response


class StubClient:
    def __init__(self, response=None, error=None):
        self.messages = StubMessages(response=response, error=error)


class StubResponse:
    def __init__(self, parsed_output, stop_reason="end_turn"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


def make_analysis():
    return PhotoAnalysis(
        items=[
            {
                "description": "Grilled salmon fillet",
                "portion_estimate": "1 medium fillet, ~150 g",
                "protein_grams": 34.0,
                "carbs_grams": 0.0,
                "fat_grams": 18.0,
                "fiber_grams": 0.0,
                "calories": 300.0,
            }
        ],
        notes="Portion size estimated from plate size; no visible sauce.",
    )


def test_analyze_food_photo_returns_parsed_output():
    analysis = make_analysis()
    client = StubClient(response=StubResponse(analysis))

    result = analyze_food_photo(b"fake-bytes", "image/jpeg", client=client)

    assert result.items[0].description == "Grilled salmon fillet"
    assert result.items[0].protein_grams == 34.0
    assert client.messages.last_kwargs["output_format"] is PhotoAnalysis


def test_analyze_food_photo_sends_base64_image_content():
    client = StubClient(response=StubResponse(make_analysis()))

    analyze_food_photo(b"fake-bytes", "image/png", client=client)

    content = client.messages.last_kwargs["messages"][0]["content"]
    image_block = next(block for block in content if block["type"] == "image")
    assert image_block["source"]["media_type"] == "image/png"
    assert image_block["source"]["type"] == "base64"


def test_analyze_food_photo_rejects_empty_bytes():
    with pytest.raises(FoodPhotoError, match="No photo"):
        analyze_food_photo(b"", "image/jpeg", client=StubClient())


def test_analyze_food_photo_rejects_oversized_photo():
    oversized = b"x" * (MAX_PHOTO_BYTES + 1)

    with pytest.raises(FoodPhotoError, match="too large"):
        analyze_food_photo(oversized, "image/jpeg", client=StubClient())


def test_analyze_food_photo_requires_api_key_without_injected_client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(FoodPhotoError, match="No Anthropic API key"):
        analyze_food_photo(b"fake-bytes", "image/jpeg", api_key=None, client=None)


def test_analyze_food_photo_raises_on_refusal():
    client = StubClient(response=StubResponse(make_analysis(), stop_reason="refusal"))

    with pytest.raises(FoodPhotoError, match="declined"):
        analyze_food_photo(b"fake-bytes", "image/jpeg", client=client)


def test_analyze_food_photo_wraps_authentication_error():
    error = anthropic.AuthenticationError(
        message="bad key", response=_fake_httpx_response(401), body=None
    )
    client = StubClient(error=error)

    with pytest.raises(FoodPhotoError, match="rejected the API key"):
        analyze_food_photo(b"fake-bytes", "image/jpeg", client=client)


def test_analyze_food_photo_wraps_rate_limit_error():
    error = anthropic.RateLimitError(
        message="slow down", response=_fake_httpx_response(429), body=None
    )
    client = StubClient(error=error)

    with pytest.raises(FoodPhotoError, match="rate limit"):
        analyze_food_photo(b"fake-bytes", "image/jpeg", client=client)


def test_analyze_food_photo_wraps_connection_error():
    error = anthropic.APIConnectionError(request=_fake_httpx_request())
    client = StubClient(error=error)

    with pytest.raises(FoodPhotoError, match="Could not reach"):
        analyze_food_photo(b"fake-bytes", "image/jpeg", client=client)


def test_get_api_key_prefers_environment_variable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    assert get_api_key({"anthropic_api_key": "secret-key"}) == "env-key"


def test_get_api_key_falls_back_to_secrets(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert get_api_key({"anthropic_api_key": "secret-key"}) == "secret-key"


def test_get_api_key_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert get_api_key(None) is None


def test_get_api_key_ignores_secrets_that_raise_on_bool_check(monkeypatch):
    """st.secrets raises on truthiness (not just .get) when there is no
    secrets.toml at all — a bare ``if secrets:`` must not crash either."""

    class BoolExplodingSecrets:
        def __bool__(self):
            raise RuntimeError("no secrets file")

        def get(self, key, default=None):
            raise RuntimeError("no secrets file")

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert get_api_key(BoolExplodingSecrets()) is None


def _fake_httpx_request():
    # This SDK version vendors httpx as httpx2 (see anthropic 0.x -> 1.x
    # upgrade notes); exception constructors type-check against it.
    import httpx2

    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def _fake_httpx_response(status_code):
    import httpx2

    return httpx2.Response(status_code, request=_fake_httpx_request())
