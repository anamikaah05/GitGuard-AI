"""
services/secret_service.py — ML inference for secret detection

Uses the TF-IDF vectorizer + Logistic Regression model trained on the
ProwlBench dataset. The model classifies a text snippet as containing a
secret (class 1) or being safe (class 0).

Flow:
  text → TF-IDF transform → Logistic Regression → label + confidence
"""

from __future__ import annotations

import logging
import numpy as np

from core.exceptions import ModelNotLoadedError
from models.loader import get_model_registry

logger = logging.getLogger(__name__)


class SecretPrediction:
    """Value object returned by the secret detection service."""
    __slots__ = ("label", "confidence", "is_secret")

    def __init__(self, label: int, confidence: float) -> None:
        self.label = label
        self.confidence = round(float(confidence), 4)
        self.is_secret = label == 1

    @property
    def ml_label(self) -> str:
        return "SECRET" if self.is_secret else "SAFE"


def predict_secret(text: str) -> SecretPrediction:
    """
    Run ML secret detection on *text*.

    Parameters
    ----------
    text: Raw code or text snippet to classify.

    Returns
    -------
    SecretPrediction with the predicted label and confidence.

    Raises
    ------
    ModelNotLoadedError: If models have not been loaded at startup.
    ValueError:          If *text* is empty.
    """
    if not text or not text.strip():
        raise ValueError("Input text must not be empty.")

    registry = get_model_registry()
    if registry.tfidf_vectorizer is None or registry.secret_model is None:
        raise ModelNotLoadedError(
            "Secret detection models are not loaded. "
            "Ensure load_models() was called at application startup."
        )

    # Vectorise
    X = registry.tfidf_vectorizer.transform([text])

    # Predict
    # Predict probabilities
    proba: np.ndarray = registry.secret_model.predict_proba(X)[0]

    # Class order confirmed: 0 = SAFE, 1 = SECRET
    secret_probability = float(proba[1])

    # Experimental precision-focused threshold
    SECRET_THRESHOLD = 0.70

    label = 1 if secret_probability >= SECRET_THRESHOLD else 0

    confidence = float(proba[label])

    logger.debug("Secret scan: label=%d confidence=%.4f", label, confidence)
    return SecretPrediction(label=label, confidence=confidence)
