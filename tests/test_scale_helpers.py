import unittest

from src.scale_helpers import (
    calculate_net_group_percentages,
    calculate_net_score,
    format_net_score,
    format_net_group_line,
    is_scale_question,
    normalize_scale_option,
    order_scale_categories_and_values,
)


class TestScaleHelpers(unittest.TestCase):
    def test_dont_know_is_ignored_for_scale_detection_and_net_score(self):
        categories = [
            "Agree",
            "Don't know",
            "Strongly disagree",
            "Strongly agree",
            "Disagree",
            "Neither agree nor disagree",
        ]
        values = [0.25, 0.10, 0.05, 0.35, 0.15, 0.10]

        self.assertEqual(normalize_scale_option("Don't know"), "don t know")
        self.assertTrue(is_scale_question(categories))
        self.assertEqual(calculate_net_score(categories, values), 40)
        self.assertEqual(format_net_score(40), "Net score: +40")
        self.assertEqual(
            calculate_net_group_percentages(categories, values),
            {
                "positive_label": "Net agree",
                "negative_label": "Net disagree",
                "positive_pct": 60,
                "negative_pct": 20,
            },
        )
        self.assertEqual(format_net_group_line("Net agree", 60), "Net agree: 60%")

        ordered = order_scale_categories_and_values(categories, values)
        self.assertIsNotNone(ordered)
        ordered_categories, ordered_values = ordered
        self.assertEqual(
            ordered_categories,
            [
                "Strongly agree",
                "Agree",
                "Neither agree nor disagree",
                "Disagree",
                "Strongly disagree",
                "Don't know",
            ],
        )
        self.assertEqual(ordered_values, [0.35, 0.25, 0.10, 0.15, 0.05, 0.10])

    def test_normal_categorical_question_is_not_a_scale(self):
        categories = ["Lloyds", "Barclays", "Halifax", "Don't know"]
        values = [0.3, 0.25, 0.2, 0.25]

        self.assertFalse(is_scale_question(categories))
        self.assertIsNone(calculate_net_score(categories, values))
        self.assertIsNone(calculate_net_group_percentages(categories, values))
        self.assertIsNone(order_scale_categories_and_values(categories, values))

    def test_scale_family_labels_are_specific_to_response_options(self):
        likely_categories = [
            "Very likely",
            "Likely",
            "Neutral",
            "Unlikely",
            "Very unlikely",
        ]
        likely_values = [0.10, 0.45, 0.20, 0.15, 0.10]

        self.assertEqual(
            calculate_net_group_percentages(likely_categories, likely_values),
            {
                "positive_label": "Net likely",
                "negative_label": "Net unlikely",
                "positive_pct": 55,
                "negative_pct": 25,
            },
        )


if __name__ == "__main__":
    unittest.main()
