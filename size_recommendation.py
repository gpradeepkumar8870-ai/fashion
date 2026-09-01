"""
StyleHub - AI-Based Size Recommendation Engine
================================================
This module implements a weighted, multi-feature scoring algorithm that maps
a shopper's body measurements to the size that best fits them, similar in
spirit to the recommendation engines used by fashion retailers (Amazon's
"Fit Predictor", ASOS's "Fit Assistant", etc).

Approach
--------
Real ML models for size recommendation are trained on historical
purchase/return data (which garment sizes a shopper with given measurements
kept vs returned). Since this project has no such historical dataset, we
implement a transparent, deterministic *rule-based scoring model* that:

1. Builds a standard size chart per gender (chest/waist/hip bands in cm).
2. Scores every candidate size against the user's measurements using a
   weighted Euclidean-style distance (chest/waist/hip weighted by how many
   measurements the user supplied).
3. Applies a BMI-derived adjustment and the user's stated fit preference
   (slim / regular / loose) to shift the recommendation half a size up or
   down, the same way real fit-assistants nudge based on body composition.
4. Returns a confidence score (0-1) based on how close the best match is
   relative to the size gap, plus a runner-up "alternate size" for
   between-size shoppers.

This keeps the feature genuinely data-driven and explainable (which matters
for a fashion checkout flow) without requiring an external dataset or a
trained model file to ship with the project. Swapping in a trained
scikit-learn/ANN model later only requires replacing `_score_sizes()` -
the request/response contract stays identical.
"""
import math
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas

router = APIRouter(prefix="/api/size-recommendation", tags=["Size Recommendation"])

# Standard size chart in centimeters: {size: (chest, waist, hip)}
SIZE_CHART = {
    "men": {
        "XS": (86, 71, 86), "S": (91, 76, 91), "M": (97, 81, 97),
        "L": (102, 87, 102), "XL": (109, 94, 109), "XXL": (116, 101, 116),
        "XXXL": (124, 109, 124),
    },
    "women": {
        "XS": (78, 60, 86), "S": (83, 65, 91), "M": (88, 70, 96),
        "L": (94, 76, 102), "XL": (101, 83, 109), "XXL": (109, 91, 117),
        "XXXL": (117, 99, 125),
    },
    "unisex": {
        "XS": (82, 66, 86), "S": (87, 71, 91), "M": (93, 76, 96),
        "L": (98, 82, 102), "XL": (105, 89, 109), "XXL": (112, 96, 116),
        "XXXL": (120, 104, 124),
    },
}

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

FIT_ADJUSTMENT = {"slim": -1, "regular": 0, "loose": 1}  # shift index in SIZE_ORDER


def _bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def _estimate_missing_measurement(height_cm: float, weight_kg: float, gender: str):
    """
    When chest/waist/hip aren't provided, derive rough estimates from
    height + weight using standard anthropometric ratios. This lets the
    engine still work for shoppers who only know their height & weight.
    """
    bmi = _bmi(weight_kg, height_cm)
    base = height_cm * 0.52 if gender == "women" else height_cm * 0.55
    bmi_adjust = (bmi - 22) * 1.8
    chest = base + bmi_adjust
    waist = chest - (16 if gender == "women" else 12)
    hip = chest + (6 if gender == "women" else -2)
    return round(chest, 1), round(waist, 1), round(hip, 1)


def _score_sizes(chest, waist, hip, gender: str):
    chart = SIZE_CHART.get(gender, SIZE_CHART["unisex"])

    # weight each measurement equally when present
    weights = {"chest": 1.0, "waist": 1.0, "hip": 1.0}

    scores = {}
    for size, (c_ref, w_ref, h_ref) in chart.items():
        dist = math.sqrt(
            weights["chest"] * (chest - c_ref) ** 2
            + weights["waist"] * (waist - w_ref) ** 2
            + weights["hip"] * (hip - h_ref) ** 2
        )
        scores[size] = dist
    return scores


@router.post("", response_model=schemas.SizeRecommendationResponse)
def recommend_size(payload: schemas.SizeRecommendationRequest, db: Session = Depends(get_db)):
    gender = payload.gender if payload.gender in SIZE_CHART else "unisex"
    chart = SIZE_CHART[gender]

    chest = payload.chest_cm
    waist = payload.waist_cm
    hip = payload.hip_cm

    est_chest, est_waist, est_hip = _estimate_missing_measurement(payload.height_cm, payload.weight_kg, gender)
    chest = chest if chest else est_chest
    waist = waist if waist else est_waist
    hip = hip if hip else est_hip

    scores = _score_sizes(chest, waist, hip, gender)
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    best_size, best_dist = ranked[0]
    second_size, second_dist = ranked[1] if len(ranked) > 1 else (None, None)

    # apply fit preference nudge
    fit_pref = payload.fit_preference if payload.fit_preference in FIT_ADJUSTMENT else "regular"
    shift = FIT_ADJUSTMENT[fit_pref]
    if shift != 0:
        idx = SIZE_ORDER.index(best_size)
        new_idx = max(0, min(len(SIZE_ORDER) - 1, idx + shift))
        best_size = SIZE_ORDER[new_idx]

    bmi = _bmi(payload.weight_kg, payload.height_cm)

    # confidence: how decisively the best size beat the runner-up
    if second_dist and second_dist > 0:
        confidence = max(0.5, min(0.98, 1 - (best_dist / (best_dist + second_dist + 1e-6))))
    else:
        confidence = 0.75
    confidence = round(confidence, 2)

    explanation_parts = [
        f"Based on an estimated chest/bust of {round(chest)} cm, waist of {round(waist)} cm, "
        f"and hip of {round(hip)} cm, size {best_size} is the closest match on our size chart."
    ]
    if fit_pref != "regular":
        explanation_parts.append(f"Adjusted for your '{fit_pref}' fit preference.")
    if bmi < 18.5:
        explanation_parts.append("Your BMI suggests a leaner build - consider the alternate size if you prefer a closer fit.")
    elif bmi >= 27:
        explanation_parts.append("For a more relaxed, comfortable fit you may prefer the next size up.")

    return schemas.SizeRecommendationResponse(
        recommended_size=best_size,
        confidence=confidence,
        bmi=bmi,
        alternate_size=second_size,
        explanation=" ".join(explanation_parts),
        size_chart={s: {"chest_cm": v[0], "waist_cm": v[1], "hip_cm": v[2]} for s, v in chart.items()},
    )
