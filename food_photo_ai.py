"""AI-assisted food identification from a photo, using Claude's vision input.

This calls the Claude API (a paid, external service) to look at a photo and
guess what food is in it and roughly how much protein/carbs/fat/fiber/calories
it contains. These are visual estimates from a general-purpose model, not a
lab measurement or a barcode lookup — the app always shows them for the user
to review and edit before saving, exactly like the other lookup sources.

Requires an Anthropic API key: the ANTHROPIC_API_KEY environment variable, or
an `anthropic_api_key` entry in .streamlit/secrets.toml. No key ships with
this project.
"""

import base64
import os
from typing import List, Optional

import anthropic
from pydantic import BaseModel, Field


MODEL_ID = "claude-opus-5"
MAX_TOKENS = 4096

# The Claude API's per-image size limit is 5 MB; reject earlier with a clear
# message instead of letting the request fail.
MAX_PHOTO_BYTES = 5 * 1024 * 1024

ANALYSIS_PROMPT = (
    "Identify each distinct food or dish visible in this photo. For each one, "
    "give a short description, a plain-language portion estimate based on "
    "what's visible in the photo (plate size, comparison to common objects, "
    "etc.), and your best-guess macros (protein, carbs, fat, fiber in grams, "
    "and calories) for that portion. These are rough visual estimates, not "
    "lab measurements — note in `notes` anything that makes the photo hard to "
    "judge (hidden sauce or dressing, unclear portion size, a mixed dish with "
    "ingredients you can't see, etc.). Do not include food safety, dietary, or "
    "health advice — just identify what's shown and estimate its macros."
)


class DetectedFoodItem(BaseModel):
    description: str = Field(
        description="Short name of the food or dish identified in the photo"
    )
    portion_estimate: str = Field(
        description=(
            "Plain-language estimate of the portion shown, e.g. '1 cup', "
            "'150 g', '1 medium fillet'"
        )
    )
    protein_grams: Optional[float] = Field(
        default=None, description="Estimated protein in grams for the portion shown"
    )
    carbs_grams: Optional[float] = Field(
        default=None,
        description="Estimated carbohydrate grams for the portion shown",
    )
    fat_grams: Optional[float] = Field(
        default=None, description="Estimated fat grams for the portion shown"
    )
    fiber_grams: Optional[float] = Field(
        default=None, description="Estimated fiber grams for the portion shown"
    )
    calories: Optional[float] = Field(
        default=None, description="Estimated calories for the portion shown"
    )


class PhotoAnalysis(BaseModel):
    items: List[DetectedFoodItem] = Field(
        description="One entry per distinct food or dish visible in the photo"
    )
    notes: str = Field(
        description=(
            "One or two sentences noting anything that makes the estimate "
            "uncertain. Empty string if nothing notable."
        )
    )


class FoodPhotoError(Exception):
    """Raised when a photo can't be analyzed."""


def get_api_key(secrets=None):
    """Return the Anthropic API key to use, or None if none is configured."""
    environment_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if environment_key:
        return environment_key

    if secrets is not None:
        try:
            secret_key = str(secrets.get("anthropic_api_key", "")).strip()
        except Exception:
            # st.secrets raises on any access (even truthiness) when no
            # secrets.toml file exists at all.
            secret_key = ""
        if secret_key:
            return secret_key

    return None


def analyze_food_photo(image_bytes, media_type, api_key=None, client=None):
    """Send a food photo to Claude and return identified items with estimated macros.

    ``client`` lets tests inject a stub instead of making a real API call.
    """
    if not image_bytes:
        raise FoodPhotoError("No photo to analyze.")

    if len(image_bytes) > MAX_PHOTO_BYTES:
        raise FoodPhotoError(
            f"Photo is too large ({len(image_bytes) / 1_000_000:.1f} MB). "
            "Please use a photo under 5 MB."
        )

    api_key = api_key if api_key is not None else get_api_key()
    if client is None and not api_key:
        raise FoodPhotoError(
            "No Anthropic API key configured. Set the ANTHROPIC_API_KEY "
            "environment variable, or add anthropic_api_key to "
            ".streamlit/secrets.toml, to use AI photo analysis."
        )

    requester = client or anthropic.Anthropic(api_key=api_key)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = requester.messages.parse(
            model=MODEL_ID,
            max_tokens=MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
            output_format=PhotoAnalysis,
        )
    except anthropic.AuthenticationError as error:
        raise FoodPhotoError(
            "Anthropic rejected the API key. Check ANTHROPIC_API_KEY."
        ) from error
    except anthropic.RateLimitError as error:
        raise FoodPhotoError(
            "Anthropic rate limit reached. Try again shortly."
        ) from error
    except anthropic.APIConnectionError as error:
        raise FoodPhotoError(
            f"Could not reach the Anthropic API: {error}"
        ) from error
    except anthropic.APIStatusError as error:
        raise FoodPhotoError(f"Anthropic API error: {error.message}") from error

    if response.stop_reason == "refusal":
        raise FoodPhotoError("Claude declined to analyze this photo.")

    return response.parsed_output
