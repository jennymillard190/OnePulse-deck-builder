import unittest
import pandas as pd
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import sys
import streamlit as st
from src.data_loader import load_uploaded_file

# Add the src directory to the path so we can import app functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the functions we want to test from their new modules
from src.ui_helpers import clean_age_data
from src.template_matcher import (
    load_prebuilt_templates, 
    find_matching_column, 
    find_matching_values,
    get_applicable_templates,
    add_prebuilt_template,
    get_column_values
)

class TestAgeDataCleaning(unittest.TestCase):
    """Test age data cleaning functionality"""
    
    def setUp(self):
        """Set up test data with various age formats"""
        self.test_data = pd.DataFrame({
            'Age range': ['25', '30;31', '35', '40;41;42', '45', '50', '55', '60', '65', '70'],
            'Gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female'],
            'Other': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        })
    
    def test_clean_age_data_removes_semicolon_values(self):
        """Test that semicolon-separated values are removed"""
        cleaned_df = clean_age_data(self.test_data.copy())
        
        # Check that rows with semicolons are removed
        self.assertNotIn('30;31', cleaned_df['Age range'].values)
        self.assertNotIn('40;41;42', cleaned_df['Age range'].values)
        
        # Check that clean values remain (now as integers, not strings)
        self.assertIn(25, cleaned_df['Age range'].values)
        self.assertIn(35, cleaned_df['Age range'].values)
        self.assertIn(45, cleaned_df['Age range'].values)
    
    def test_clean_age_data_converts_to_numeric(self):
        """Test that age values are converted to numeric"""
        cleaned_df = clean_age_data(self.test_data.copy())
        
        # Check that Age range column is numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(cleaned_df['Age range']))
        
        # Check that values are properly converted
        self.assertIn(25, cleaned_df['Age range'].values)
        self.assertIn(35, cleaned_df['Age range'].values)
        self.assertIn(45, cleaned_df['Age range'].values)
    
    def test_clean_age_data_handles_missing_column(self):
        """Test that function handles missing Age range column gracefully"""
        df_no_age = self.test_data.drop(columns=['Age range'])
        cleaned_df = clean_age_data(df_no_age)
        
        # Should return the same dataframe unchanged
        self.assertEqual(len(cleaned_df), len(df_no_age))
        self.assertListEqual(list(cleaned_df.columns), list(df_no_age.columns))
    
    def test_clean_age_data_handles_non_numeric_values(self):
        """Test that non-numeric age values are handled properly"""
        test_data_with_text = pd.DataFrame({
            'Age range': ['25', 'thirty', '35', '40', 'N/A', '50'],
            'Gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female']
        })
        
        cleaned_df = clean_age_data(test_data_with_text)
        
        # Non-numeric values should be converted to NaN and dropped
        self.assertNotIn('thirty', cleaned_df['Age range'].values)
        self.assertNotIn('N/A', cleaned_df['Age range'].values)
        
        # Numeric values should remain
        self.assertIn(25, cleaned_df['Age range'].values)
        self.assertIn(35, cleaned_df['Age range'].values)
        self.assertIn(40, cleaned_df['Age range'].values)
        self.assertIn(50, cleaned_df['Age range'].values)

class TestTemplateLoading(unittest.TestCase):
    """Test pre-built template loading functionality"""
    
    def setUp(self):
        """Set up test template data"""
        self.test_templates = {
            "templates": {
                "Gender": {
                    "description": "Split respondents by gender",
                    "column_patterns": ["gender"],
                    "value_mappings": {
                        "Male": ["male", "m", "men", "man"],
                        "Female": ["female", "f", "women", "woman"]
                    },
                    "audiences": [
                        {
                            "name": "Male",
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Male"]}], "logic": "OR"}]
                        },
                        {
                            "name": "Female", 
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Female"]}], "logic": "OR"}]
                        }
                    ],
                    "group_name": "Gender"
                }
            }
        }
    
    def test_load_prebuilt_templates_success(self):
        """Test successful loading of pre-built templates"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.test_templates, f)
            template_path = f.name
        
        try:
            with patch('src.template_matcher.os.path.join', return_value=template_path):
                templates = load_prebuilt_templates()
                
                self.assertIn('templates', templates)
                self.assertIn('Gender', templates['templates'])
                self.assertEqual(templates['templates']['Gender']['description'], 
                               "Split respondents by gender")
        finally:
            os.unlink(template_path)
    
    def test_load_prebuilt_templates_file_not_found(self):
        """Test handling of missing template file"""
        with patch('src.template_matcher.os.path.join', return_value='nonexistent_file.json'):
            with patch('src.template_matcher.st.warning') as mock_warning:
                templates = load_prebuilt_templates()
                
                self.assertEqual(templates, {"templates": {}})
                mock_warning.assert_called_once()
    
    def test_load_prebuilt_templates_invalid_json(self):
        """Test handling of invalid JSON in template file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("This is not valid JSON")
            template_path = f.name
        
        try:
            with patch('src.template_matcher.os.path.join', return_value=template_path):
                with patch('src.template_matcher.st.error') as mock_error:
                    templates = load_prebuilt_templates()
                    
                    self.assertEqual(templates, {"templates": {}})
                    mock_error.assert_called_once()
        finally:
            os.unlink(template_path)

class TestColumnMatching(unittest.TestCase):
    """Test column matching functionality"""
    
    def test_find_matching_column_exact_match(self):
        """Test exact column name matching"""
        column_patterns = ["gender"]
        available_columns = ["Gender", "Age", "Income"]
        
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, "Gender")
    
    def test_find_matching_column_case_insensitive(self):
        """Test case-insensitive column matching"""
        column_patterns = ["GENDER"]
        available_columns = ["gender", "age", "income"]
        
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, "gender")
    
    def test_find_matching_column_partial_match(self):
        """Test partial column name matching"""
        column_patterns = ["age"]
        available_columns = ["Age range", "Gender", "Income"]
        
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, "Age range")
    
    def test_find_matching_column_no_match(self):
        """Test when no matching column is found"""
        column_patterns = ["nonexistent"]
        available_columns = ["Gender", "Age", "Income"]
        
        result = find_matching_column(column_patterns, available_columns)
        self.assertIsNone(result)
    
    def test_find_matching_column_multiple_patterns(self):
        """Test matching with multiple patterns"""
        column_patterns = ["gender", "sex"]
        available_columns = ["Sex", "Age", "Income"]
        
        result = find_matching_column(column_patterns, available_columns)
        self.assertEqual(result, "Sex")

class TestValueMatching(unittest.TestCase):
    """Test value matching functionality"""
    
    def test_find_matching_values_exact_match(self):
        """Test exact value matching"""
        target_values = ["Male", "Female"]
        value_mappings = {}
        actual_values = ["Male", "Female", "Other"]
        
        result = find_matching_values(target_values, value_mappings, actual_values)
        self.assertEqual(result, ["Male", "Female"])
    
    def test_find_matching_values_with_mappings(self):
        """Test value matching with mappings"""
        target_values = ["Male", "Female"]
        value_mappings = {
            "Male": ["male", "m", "men"],
            "Female": ["female", "f", "women"]
        }
        actual_values = ["male", "f", "other"]
        
        result = find_matching_values(target_values, value_mappings, actual_values)
        self.assertEqual(result, ["male", "f"])
    
    def test_find_matching_values_no_matches(self):
        """Test when no values match"""
        target_values = ["Male", "Female"]
        value_mappings = {}
        actual_values = ["Other", "Unknown"]
        
        result = find_matching_values(target_values, value_mappings, actual_values)
        self.assertEqual(result, [])
    
    def test_find_matching_values_empty_mappings(self):
        """Test value matching with empty mappings"""
        target_values = ["Male", "Female"]
        value_mappings = {}
        actual_values = ["Male", "Female"]
        
        result = find_matching_values(target_values, value_mappings, actual_values)
        self.assertEqual(result, ["Male", "Female"])

class TestApplicableTemplates(unittest.TestCase):
    """Test applicable templates functionality"""
    
    def setUp(self):
        """Set up test data and templates"""
        self.test_data = pd.DataFrame({
            'Gender': ['Male', 'Female', 'Male', 'Female'],
            'Age range': ['25', '30', '35', '40'],
            'Other': ['A', 'B', 'C', 'D']
        })
        
        self.test_templates = {
            "templates": {
                "Gender": {
                    "description": "Split respondents by gender",
                    "column_patterns": ["gender"],
                    "value_mappings": {
                        "Male": ["male", "m", "men"],
                        "Female": ["female", "f", "women"]
                    },
                    "audiences": [
                        {
                            "name": "Male",
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Male"]}], "logic": "OR"}]
                        },
                        {
                            "name": "Female", 
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Female"]}], "logic": "OR"}]
                        }
                    ],
                    "group_name": "Gender"
                },
                "Age Groups": {
                    "description": "Split respondents by age ranges",
                    "column_patterns": ["age range"],
                    "value_mappings": {},
                    "audiences": [
                        {
                            "name": "Young Adults",
                            "groups": [{"name": "Age", "conditions": [{"column": "Age range", "values": ["25", "30"]}], "logic": "OR"}]
                        }
                    ],
                    "group_name": "Age Groups"
                }
            }
        }
    
    @patch('src.template_matcher.load_prebuilt_templates')
    @patch('src.template_matcher.get_column_values')
    def test_get_applicable_templates_gender(self, mock_get_values, mock_load_templates):
        """Test finding applicable gender template"""
        mock_load_templates.return_value = self.test_templates
        mock_get_values.return_value = ["Male", "Female"]
        
        result = get_applicable_templates(self.test_data)
        
        self.assertIn("Gender", result)
        self.assertEqual(result["Gender"]["matching_column"], "Gender")
        self.assertEqual(result["Gender"]["confidence"], "high")
    
    @patch('src.template_matcher.load_prebuilt_templates')
    @patch('src.template_matcher.get_column_values')
    def test_get_applicable_templates_age(self, mock_get_values, mock_load_templates):
        """Test finding applicable age template"""
        mock_load_templates.return_value = self.test_templates
        mock_get_values.return_value = ["25", "30", "35", "40"]
        
        result = get_applicable_templates(self.test_data)
        
        self.assertIn("Age Groups", result)
        self.assertEqual(result["Age Groups"]["matching_column"], "Age range")
        self.assertEqual(result["Age Groups"]["confidence"], "medium")
    
    @patch('src.template_matcher.load_prebuilt_templates')
    def test_get_applicable_templates_no_data(self, mock_load_templates):
        """Test when no data is provided"""
        mock_load_templates.return_value = self.test_templates
        
        result = get_applicable_templates(None)
        
        self.assertEqual(result, {})
    
    @patch('src.template_matcher.load_prebuilt_templates')
    @patch('src.template_matcher.get_column_values')
    def test_get_applicable_templates_no_matching_columns(self, mock_get_values, mock_load_templates):
        """Test when no columns match the patterns"""
        mock_load_templates.return_value = self.test_templates
        mock_get_values.return_value = []
        
        # Data with no matching columns
        test_data = pd.DataFrame({
            'Other': ['A', 'B', 'C'],
            'Another': ['X', 'Y', 'Z']
        })
        
        result = get_applicable_templates(test_data)
        
        self.assertEqual(result, {})

class TestTemplateApplication(unittest.TestCase):
    """Test template application functionality"""
    
    def setUp(self):
        """Set up test data and session state"""
        self.test_data = pd.DataFrame({
            'Gender': ['Male', 'Female', 'Male', 'Female'],
            'Age range': ['25', '30', '35', '40'],
            'Other': ['A', 'B', 'C', 'D']
        })
        
        self.test_templates = {
            "Gender": {
                "template": {
                    "description": "Split respondents by gender",
                    "column_patterns": ["gender"],
                    "value_mappings": {
                        "Male": ["male", "m", "men"],
                        "Female": ["female", "f", "women"]
                    },
                    "audiences": [
                        {
                            "name": "Male",
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Male"]}], "logic": "OR"}]
                        },
                        {
                            "name": "Female", 
                            "groups": [{"name": "Gender", "conditions": [{"column": "Gender", "values": ["Female"]}], "logic": "OR"}]
                        }
                    ],
                    "group_name": "Gender"
                },
                "matching_column": "Gender"
            }
        }
    
    @patch('src.template_matcher.st.error')
    @patch('src.template_matcher.st.warning')
    @patch('src.template_matcher.st.success')
    @patch('src.template_matcher.st.rerun')
    @patch('src.template_matcher.get_column_values')
    def test_add_prebuilt_template_success(self, mock_get_values, mock_rerun, mock_success, mock_warning, mock_error):
        """Test successful template application"""
        mock_get_values.return_value = ["Male", "Female"]
        
        # Mock session state with proper DataFrame structure
        from unittest.mock import MagicMock
        mock_session = MagicMock()
        mock_session.audiences = []
        mock_session.audience_groups = []
        
        # Create a mock DataFrame that can handle the dtype access
        mock_df = MagicMock()
        mock_column = MagicMock()
        mock_column.dtype = 'object'  # String dtype for gender column
        mock_df.__getitem__.return_value = mock_column
        mock_session.get.return_value = mock_df
        
        with patch('src.template_matcher.st.session_state', mock_session):
            mock_session.audiences = []
            mock_session.audience_groups = []
            
            # Create a mock DataFrame that can handle the dtype access
            mock_df = MagicMock()
            mock_column = MagicMock()
            mock_column.dtype = 'object'  # String dtype for gender column
            mock_df.__getitem__.return_value = mock_column
            mock_session.get.return_value = mock_df
            
            add_prebuilt_template("Gender", self.test_templates, mock_session)
            
            # Check that audiences were added
            self.assertEqual(len(mock_session.audiences), 2)
            self.assertEqual(mock_session.audiences[0]["name"], "Male")
            self.assertEqual(mock_session.audiences[1]["name"], "Female")
            
            # Check that group was added
            self.assertEqual(len(mock_session.audience_groups), 1)
            self.assertEqual(mock_session.audience_groups[0]["name"], "Gender")
            self.assertEqual(mock_session.audience_groups[0]["audiences"], ["Male", "Female"])
            
            mock_success.assert_called_once()
            mock_rerun.assert_called_once()
    
    @patch('src.template_matcher.st.error')
    def test_add_prebuilt_template_not_applicable(self, mock_error):
        """Test template application when template is not applicable"""
        from unittest.mock import MagicMock
        mock_session = MagicMock()
        add_prebuilt_template("Nonexistent", {}, mock_session)
        
        mock_error.assert_called_once()

def test_age_group_sample_sizes_real_data():
    import streamlit as st
    # Load test data using the app's loader
    test_file_path = 'tests/data/test.csv'
    with open(test_file_path, 'rb') as f:
        df = load_uploaded_file(f)
    st.session_state.df = df

    # Import app helpers from their new modules
    from src.template_matcher import get_applicable_templates, add_prebuilt_template

    # Get applicable templates
    applicable = get_applicable_templates(df)
    assert 'Age Groups' in applicable, "Age Groups template should be applicable"

    # Clear audiences/groups
    st.session_state.audiences = []
    st.session_state.audience_groups = []

    # Add the Age Groups template
    add_prebuilt_template('Age Groups', applicable, st.session_state)

    # Now, for each audience, calculate sample size using the same logic as the app
    nonzero_count = 0
    for aud in st.session_state.audiences:
        group_masks = []
        for group in aud["groups"]:
            masks = []
            for cond in group["conditions"]:
                col = cond.get("column")
                vals = cond.get("values", [])
                if col and vals:
                    masks.append(df[col].isin(vals))
            if masks:
                if group.get("logic", "OR") == "AND":
                    group_mask = masks[0]
                    for m in masks[1:]:
                        group_mask &= m
                else:
                    group_mask = masks[0]
                    for m in masks[1:]:
                        group_mask |= m
                group_masks.append(group_mask)
        if group_masks:
            if aud.get("top_logic", "OR") == "AND":
                total_mask = group_masks[0]
                for m in group_masks[1:]:
                    total_mask &= m
            else:
                total_mask = group_masks[0]
                for m in group_masks[1:]:
                    total_mask |= m
            sample_size = df[total_mask].shape[0]
            print(f"Audience {aud['name']} sample size: {sample_size}")
            if sample_size > 0:
                nonzero_count += 1
    assert nonzero_count > 0, "At least one age group should have a nonzero sample size with real data"

def test_age_group_with_semicolon_values():
    """Test age group template with semicolon-separated values in the data"""
    # Create test data with semicolon-separated values
    test_data = pd.DataFrame({
        'Age range': ['25', '30;31', '35', '40;41;42', '45', '50', '55', '60', '65', '70'],
        'Gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female']
    })
    
    # Clean the data
    from src.ui_helpers import clean_age_data
    cleaned_df = clean_age_data(test_data.copy())
    
    # Set up session state
    import streamlit as st
    st.session_state.df = cleaned_df
    
    # Import app helpers from their new modules
    from src.template_matcher import get_applicable_templates, add_prebuilt_template
    
    # Get applicable templates
    applicable = get_applicable_templates(cleaned_df)
    assert 'Age Groups' in applicable, "Age Groups template should be applicable"
    
    # Clear audiences/groups
    st.session_state.audiences = []
    st.session_state.audience_groups = []
    
    # Add the Age Groups template
    add_prebuilt_template('Age Groups', applicable, st.session_state)
    
    # Check that audiences were created
    assert len(st.session_state.audiences) > 0, "Audiences should be created"
    
    # Check that at least one audience has a nonzero sample size
    nonzero_count = 0
    for aud in st.session_state.audiences:
        group_masks = []
        for group in aud["groups"]:
            masks = []
            for cond in group["conditions"]:
                col = cond.get("column")
                vals = cond.get("values", [])
                if col and vals:
                    masks.append(cleaned_df[col].isin(vals))
            if masks:
                if group.get("logic", "OR") == "AND":
                    group_mask = masks[0]
                    for m in masks[1:]:
                        group_mask &= m
                else:
                    group_mask = masks[0]
                    for m in masks[1:]:
                        group_mask |= m
                group_masks.append(group_mask)
        if group_masks:
            if aud.get("top_logic", "OR") == "AND":
                total_mask = group_masks[0]
                for m in group_masks[1:]:
                    total_mask &= m
            else:
                total_mask = group_masks[0]
                for m in group_masks[1:]:
                    total_mask |= m
            sample_size = cleaned_df[total_mask].shape[0]
            print(f"Audience {aud['name']} sample size: {sample_size}")
            if sample_size > 0:
                nonzero_count += 1
    
    assert nonzero_count > 0, "At least one age group should have a nonzero sample size after cleaning semicolon values"

if __name__ == '__main__':
    unittest.main() 