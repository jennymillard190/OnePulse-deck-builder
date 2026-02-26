import unittest
import pandas as pd
import numpy as np
import sys
import os

# Import the function from its new module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../'))
from src.template_matcher import find_matching_column

class TestTemplateMatching(unittest.TestCase):
    def test_find_matching_column_with_float_pattern(self):
        """
        Regression test: find_matching_column should skip float/NaN/None patterns and not raise AttributeError.
        """
        available_columns = ['Gender', 'Age', 'Location']
        # Patterns include a string, a float, and a NaN
        column_patterns = ['gender', 1.23, np.nan, None]
        # Should match 'Gender' column (case-insensitive)
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, 'Gender')

    def test_find_matching_column_with_all_invalid_patterns(self):
        """
        Should return None if all patterns are invalid types.
        """
        available_columns = ['Gender', 'Age', 'Location']
        column_patterns = [1.23, np.nan, None]
        result = find_matching_column(column_patterns, available_columns)
        self.assertIsNone(result)

    def test_find_matching_column_with_invalid_column_names(self):
        """
        Should skip invalid column names (float/NaN/None) and not raise AttributeError.
        """
        available_columns = ['Gender', 1.23, np.nan, None, 'Age']
        column_patterns = ['gender']
        # Should match 'Gender' column (case-insensitive) and skip invalid columns
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, 'Gender')

if __name__ == '__main__':
    unittest.main() 