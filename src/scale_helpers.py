"""
Helpers for recognised scale questions.

Scale detection is intentionally based on response option text only. The rest of
the app continues to pass chart data as (title, categories, segments).
"""
import re
from typing import Dict, List, Optional, Sequence, Tuple


ScaleMatch = List[Tuple[str, int]]


_IGNORED_OPTIONS = {
    "don t know",
    "dont know",
    "do not know",
    "not sure",
    "not applicable",
    "na",
    "n a",
    "none of these",
    "prefer not to say",
}


_SCALE_ORDERS = [
    {
        "positive_label": "Net agree",
        "negative_label": "Net disagree",
        "options": [
            (2, ["strongly agree"]),
            (1, ["agree"]),
            (0, ["neither agree nor disagree", "neutral", "neither"]),
            (-1, ["disagree"]),
            (-2, ["strongly disagree"]),
        ],
    },
    {
        "positive_label": "Net likely",
        "negative_label": "Net unlikely",
        "options": [
            (2, ["very likely"]),
            (1, ["likely"]),
            (0, ["neither likely nor unlikely", "neutral", "neither"]),
            (-1, ["unlikely"]),
            (-2, ["very unlikely"]),
        ],
    },
    {
        "positive_label": "Net satisfied",
        "negative_label": "Net dissatisfied",
        "options": [
            (2, ["very satisfied"]),
            (1, ["satisfied"]),
            (0, ["neither satisfied nor dissatisfied", "neutral", "neither"]),
            (-1, ["dissatisfied"]),
            (-2, ["very dissatisfied"]),
        ],
    },
    {
        "positive_label": "Net good",
        "negative_label": "Net poor",
        "options": [
            (2, ["excellent"]),
            (1, ["good"]),
            (0, ["average", "fair", "neither good nor poor", "neutral", "neither"]),
            (-1, ["poor"]),
            (-2, ["very poor"]),
        ],
    },
    {
        "positive_label": "Net positive",
        "negative_label": "Net negative",
        "options": [
            (2, ["very positive"]),
            (1, ["positive"]),
            (0, ["neither positive nor negative", "neutral", "neither"]),
            (-1, ["negative"]),
            (-2, ["very negative"]),
        ],
    },
]


def _build_option_scores(scale_order: Dict[str, object]) -> Dict[str, int]:
    return {
        normalize_scale_option(label): score
        for score, labels in scale_order["options"]
        for label in labels
    }


def normalize_scale_option(option: object) -> str:
    """Normalize response option text for scale matching."""
    text = str(option).strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _match_explicit_scale(
    normalized_categories: Sequence[Tuple[str, str]]
) -> Optional[Dict[str, object]]:
    """Match one of the explicitly configured scale families."""
    for scale_order in _SCALE_ORDERS:
        option_scores = _build_option_scores(scale_order)

        matched: ScaleMatch = []
        unknown = []
        for category, normalized in normalized_categories:
            if normalized in option_scores:
                matched.append((category, option_scores[normalized]))
            elif normalized in _IGNORED_OPTIONS:
                continue
            else:
                unknown.append(category)

        if unknown:
            continue

        scores = {score for _, score in matched}
        if 2 in scores and 1 in scores and -1 in scores and -2 in scores:
            return {
                "match": matched,
                "positive_label": scale_order["positive_label"],
                "negative_label": scale_order["negative_label"],
            }

    return None


def _parse_generic_scale_option(normalized: str) -> Optional[Tuple[int, str, Optional[str]]]:
    """Parse generic Very/Quite/Neither scale wording."""
    match = re.fullmatch(r"very ([a-z0-9 ]+)", normalized)
    if match:
        return 2, match.group(1).strip(), None

    match = re.fullmatch(r"quite ([a-z0-9 ]+)", normalized)
    if match:
        return 1, match.group(1).strip(), None

    match = re.fullmatch(r"neither ([a-z0-9 ]+) nor ([a-z0-9 ]+)", normalized)
    if match:
        return 0, match.group(1).strip(), match.group(2).strip()

    return None


def _match_generic_scale(
    normalized_categories: Sequence[Tuple[str, str]]
) -> Optional[Dict[str, object]]:
    """
    Match generic five-point semantic scales.

    Required roles are: Very X, Quite X, Neither X nor Y, Quite Y, Very Y.
    """
    parsed_options = []
    for category, normalized in normalized_categories:
        if normalized in _IGNORED_OPTIONS:
            continue

        parsed = _parse_generic_scale_option(normalized)
        if parsed is None:
            return None

        score, term, neutral_negative_term = parsed
        parsed_options.append((category, score, term, neutral_negative_term))

    if len(parsed_options) < 5:
        return None

    neutral_options = [
        item for item in parsed_options
        if item[1] == 0 and item[3] is not None
    ]
    if len(neutral_options) != 1:
        return None

    _, _, positive_term, negative_term = neutral_options[0]
    required_roles = {
        (2, positive_term),
        (1, positive_term),
        (-1, negative_term),
        (-2, negative_term),
    }
    found_roles = set()
    matched: ScaleMatch = []

    for category, score, term, _ in parsed_options:
        if score == 0:
            if term != positive_term:
                return None
            matched.append((category, 0))
        elif term == positive_term and score in (1, 2):
            found_roles.add((score, term))
            matched.append((category, score))
        elif term == negative_term and score in (1, 2):
            negative_score = -score
            found_roles.add((negative_score, term))
            matched.append((category, negative_score))
        else:
            return None

    if required_roles != found_roles:
        return None

    return {
        "match": matched,
        "positive_label": f"Net {positive_term}",
        "negative_label": f"Net {negative_term}",
    }


def _get_scale_info(categories: Sequence[str]) -> Optional[Dict[str, object]]:
    normalized_categories = [
        (category, normalize_scale_option(category))
        for category in categories
    ]

    explicit_match = _match_explicit_scale(normalized_categories)
    if explicit_match is not None:
        return explicit_match

    return _match_generic_scale(normalized_categories)


def get_scale_match(categories: Sequence[str]) -> Optional[ScaleMatch]:
    """
    Return recognised scale categories with their scale scores.

    The score is positive for favourable responses, negative for unfavourable
    responses, and zero for neutral/midpoint responses. Ignored options such as
    "Don't know" are allowed but excluded from the returned match.
    """
    scale_info = _get_scale_info(categories)
    if scale_info is None:
        return None
    return scale_info["match"]


def get_scale_labels(categories: Sequence[str]) -> Optional[Tuple[str, str]]:
    """Return family-specific positive and negative net labels."""
    scale_info = _get_scale_info(categories)
    if scale_info is None:
        return None

    return scale_info["positive_label"], scale_info["negative_label"]


def is_scale_question(categories: Sequence[str]) -> bool:
    """Return True when the response options match a recognised scale."""
    return get_scale_match(categories) is not None


def order_scale_categories_and_values(
    categories: Sequence[str],
    values: Sequence[float],
) -> Optional[Tuple[List[str], List[float]]]:
    """
    Return categories and values in logical scale order, or None if not a scale.

    Positive options appear first, then neutral/midpoint options, then negative
    options. Ignored options are kept at the end in their existing order.
    """
    scale_match = get_scale_match(categories)
    if scale_match is None:
        return None

    value_by_category = dict(zip(categories, values))
    score_by_category = dict(scale_match)
    original_index = {category: idx for idx, category in enumerate(categories)}

    ordered_categories = sorted(
        score_by_category,
        key=lambda category: (-score_by_category[category], original_index[category]),
    )

    ignored_categories = [
        category
        for category in categories
        if category not in score_by_category
    ]
    ordered_categories.extend(ignored_categories)

    ordered_values = [value_by_category[category] for category in ordered_categories]
    return ordered_categories, ordered_values


def calculate_net_score(categories: Sequence[str], values: Sequence[float]) -> Optional[int]:
    """
    Calculate net score as top two positive options minus bottom two negatives.

    Values are expected to be proportions, so the returned score is percentage
    points rounded to a whole number.
    """
    scale_match = get_scale_match(categories)
    if scale_match is None:
        return None

    score_by_category = dict(scale_match)
    positive = 0.0
    negative = 0.0

    for category, value in zip(categories, values):
        score = score_by_category.get(category)
        if score in (1, 2):
            positive += float(value)
        elif score in (-1, -2):
            negative += float(value)

    return round((positive - negative) * 100)


def format_net_score(score: int) -> str:
    """Format a net score with an explicit positive sign."""
    sign = "+" if score > 0 else ""
    return f"Net score: {sign}{score}"


def calculate_net_group_percentages(
    categories: Sequence[str],
    values: Sequence[float],
) -> Optional[Dict[str, object]]:
    """
    Calculate positive and negative grouped percentages for scale callouts.

    Neutral/midpoint and ignored options are excluded from both percentages.
    """
    scale_match = get_scale_match(categories)
    scale_labels = get_scale_labels(categories)
    if scale_match is None or scale_labels is None:
        return None

    score_by_category = dict(scale_match)
    positive = 0.0
    negative = 0.0

    for category, value in zip(categories, values):
        score = score_by_category.get(category)
        if score in (1, 2):
            positive += float(value)
        elif score in (-1, -2):
            negative += float(value)

    positive_label, negative_label = scale_labels
    return {
        "positive_label": positive_label,
        "negative_label": negative_label,
        "positive_pct": round(positive * 100),
        "negative_pct": round(negative * 100),
    }


def format_net_group_line(label: str, pct: int) -> str:
    """Format grouped scale percentages for callout boxes."""
    return f"{label}: {pct}%"
