import unittest
import sys
import os

class TestAppImports(unittest.TestCase):
    """Test that the main application modules can be imported without errors"""
    
    def test_app_imports(self):
        """Test that app.py can be imported without NameError or other top-level issues"""
        try:
            import app
        except Exception as e:
            self.fail(f"Importing app.py failed: {e}")
    
    def test_app_function_definitions(self):
        """Test that all functions are properly defined and can be accessed from their modules"""
        # Functions that should be importable from their respective modules
        from src.ui_helpers import clean_age_data, group_summary, audience_summary, auto_group_name
        from src.template_matcher import load_prebuilt_templates, find_matching_column, find_matching_values, get_applicable_templates, add_prebuilt_template, get_column_values
        from src.audience_utils import save_audience_definitions
        from src.ui.audience_editor import audience_editor
        
        # Verify all functions are callable
        required_functions = [
            clean_age_data,
            load_prebuilt_templates, 
            find_matching_column,
            find_matching_values,
            get_applicable_templates,
            add_prebuilt_template,
            get_column_values,
            group_summary,
            audience_summary,
            auto_group_name,
            save_audience_definitions,
            audience_editor
        ]
        
        for func in required_functions:
            self.assertTrue(callable(func), f"Function {func.__name__} is not callable")
    
    def test_src_modules_import(self):
        """Test that all src modules can be imported"""
        src_modules = [
            'src.config',
            'src.data_loader', 
            'src.data_processor',
            'src.ppt_generator',
            'src.main',
            'src.session_state',
            'src.chart_helpers',
            'src.audience_utils',
            'src.template_matcher',
            'src.ui_helpers',
            'src.ui.audience_editor'
        ]
        
        for module_name in src_modules:
            try:
                __import__(module_name)
            except Exception as e:
                self.fail(f"Importing {module_name} failed: {e}")
    
    def test_prebuilt_templates_file_exists(self):
        """Test that the prebuilt templates JSON file exists and is valid JSON"""
        template_path = os.path.join("src", "prebuilt_templates.json")
        self.assertTrue(os.path.exists(template_path), 
                       f"Prebuilt templates file not found at {template_path}")
        
        try:
            import json
            with open(template_path, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            self.fail(f"Prebuilt templates file contains invalid JSON: {e}")
        except Exception as e:
            self.fail(f"Error reading prebuilt templates file: {e}")

if __name__ == '__main__':
    unittest.main() 