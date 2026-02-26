# Test Suite Overview

This document provides a summary of the automated tests for the OnePulse Charting Automation project. It describes the main areas covered, the structure of the test suite, and what each test is checking for.

## Test Organization

All tests are located in the `tests/` directory. The main test file is `tests/test_data_processing.py`, which covers data loading, processing, and PowerPoint generation. Additional files test imports, template matching, and prebuilt template logic.

---

## Test Classes and Coverage

### 1. `TestDataLoading`
**Purpose:** Tests for correct loading and parsing of input data files (CSV, XLSX, error handling).
- `test_xlsx_loading`: Checks that XLSX files are loaded with correct headers and column formatting.
- `test_csv_loading`: Checks that CSV files are loaded with correct headers and column formatting.
- `test_file_loading_error_handling`: Ensures errors are raised for missing, invalid, or unsupported files.

### 2. `TestDataProcessing`
**Purpose:** Tests for correct processing of raw data into the expected internal format.
- `test_open_ended_questions`: Ensures open-ended questions are identified and excluded from chart data.
- `test_process_data_structure`: Checks the structure and types of processed data.
- `test_response_values`: Verifies that response values are processed as expected.
- `test_audience_filtering`: Checks that audience filters are applied correctly.
- `test_multi_select_boolean_conversion`: Ensures multi-select columns are converted to boolean.
- `test_age_of_children_processing` / `test_age_of_children_column_order`: Tests for correct handling and ordering of age-related columns.
- `test_semicolon_separated_column_processing`: Ensures semicolon-separated columns are processed correctly.
- `test_bank_columns_alphabetical_order`: Checks that bank columns are ordered alphabetically.
- `test_chart_data_ordering`: Verifies the order of chart data.

### 3. `TestDataAnalysis`
**Purpose:** Tests for correct handling of multi-select questions and data analysis logic.
- `test_multi_select_processing`: Checks that multi-select questions are processed as expected.

### 4. `TestPowerPointGeneration`
**Purpose:** Tests for PowerPoint chart creation and color assignment.
- `test_chart_creation`: Ensures charts are created in the PowerPoint output.
- `test_color_assignment`: Checks that colors are assigned correctly to chart elements.
- `test_missing_template_file_raises_clear_error`: Ensures a clear error is raised if the template file is missing.

### 5. `TestConfig`
**Purpose:** Tests for output path generation and configuration logic.
- `test_output_path_generation`: Checks that output paths are generated correctly.
- `test_output_path_absolute`: Ensures output paths are absolute.
- `test_output_path_in_project_root`: Verifies output files are placed in the project root.

### 6. `TestAppFunctionality`
**Purpose:** Tests for app-level logic, including audience definitions and sample size calculations.
- `test_pptx_filename_reflects_original_file`: Checks that output filenames reflect the input file.
- `test_audiences_appear_in_output_data`: Ensures all defined audiences appear in the output.
- `test_no_combined_data_when_no_audiences`: Checks that no combined data is generated if there are no audiences.
- `test_audience_data_structure`: Verifies the structure of audience data.
- `test_chart_titles_contain_question_text`: Ensures chart titles include the question text.
- `test_audience_groups_basic_functionality`: Checks basic audience group logic.
- `test_audience_groups_chart_structure`: Verifies the structure of group charts.
- `test_audience_groups_no_duplicate_charts`: Ensures no duplicate charts are created for groups.
- `test_audience_groups_empty_group_handling`: Checks handling of empty groups.
- `test_audience_groups_all_segments_chart`: Ensures all-segments charts are generated for groups.
- `test_audience_groups_chart_count`: Verifies the correct number of group charts.
- `test_app_sample_size_calculation`: Checks sample size calculations for audiences.
- `test_app_age_range_sample_size_calculation`: Checks sample size calculations for age ranges.
- `test_app_age_range_string_values_sample_size_calculation`: Checks sample size calculations for string-based age ranges.
- `test_age_range_audience_filtering_with_string_values`: Ensures age range filtering works with string values.

### 7. `TestPowerPointOutputStructure`
**Purpose:** Tests for the structure and content of generated PowerPoint files.
- `test_ppt_output_with_audience_groups`: Checks output with audience groups.
- `test_ppt_output_with_mixed_audiences`: Checks output with mixed grouped/ungrouped audiences.
- `test_ppt_output_no_audience_groups`: Checks output when there are no audience groups.
- `test_ppt_output_no_redundant_slides_for_grouped_audiences`: Ensures no redundant slides for grouped audiences (updated for full export behavior).
- `test_ppt_output_single_audience_no_duplicates`: Ensures no duplicate slides for a single audience.
- `test_ppt_output_chart_titles`: Checks that chart titles are formatted correctly.
- `test_ppt_output_slide_count_estimation`: Verifies slide count estimation logic.
- `test_ppt_output_integration_with_open_ended_questions`: Integration test for open-ended questions and slide counts (updated for full export behavior).
- `test_app_process_data_return_value_mismatch`: Checks for correct unpacking of process_data return values.
- `test_app_process_data_correct_unpacking`: Verifies correct unpacking and types from process_data.

### 8. `TestExportTypes`
**Purpose:** Tests for the new export type feature (Full vs Condensed PowerPoint output).
- `test_full_export_slide_order`: Checks that full export has correct slide ordering.
- `test_condensed_export_no_duplication`: Ensures condensed export has no duplicate slides.
- `test_condensed_export_structure`: Checks that condensed export has the correct structure (groups + ungrouped only).
- `test_full_export_maintains_current_behavior`: Ensures full export maintains current behavior.
- `test_export_type_parameter_validation`: Ensures invalid export types are handled gracefully.
- `test_filename_reflects_export_type`: Checks that output filenames reflect the export type.

### 9. `TestSlideOrdering`
**Purpose:** Tests for correct ordering of slides (groups before individual segments).
- `test_full_export_groups_before_individual_segments`: Checks that group slides come before individual segment slides in full export.

---

## Additional Test Files
- `test_imports.py`: Tests for import errors and module structure.
- `test_prebuilt_templates.py`: Tests for prebuilt template logic, age data cleaning, and template application.
- `test_template_matching.py`: Tests for template matching logic and column/value matching.

---

## How to Run the Tests

See the README for instructions on running the test suite with `pytest`.

---

**This document is intended to help developers and reviewers quickly understand the scope and intent of the test suite.** 