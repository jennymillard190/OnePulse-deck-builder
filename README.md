# OnePulse Charting Automation/Text Classifier

A Streamlit application for processing survey data and generating PowerPoint presentations with charts.

Also - for classifying text (survey responses to open-ended questions) – currently an independent feature, planned for integration.

### PLANS
- Recording demo instructions
- Age selections (sliders?)
- Sig testing
- Handle data with no charts (eg. only open-ended questions)
- Bar colours get repeated for multiple audiences
- Open ended responses don't need to all be listed out on the cover page!
- Audience definitions included in the output
- Audience profiles (counts, percentage of respondents, age, gender etc.)
- Sliders for faster age range selections
- Deal with open ends...
- Data cleaning for age field (eg. where "32;33" appears - what looks like bot responses...)
- Special characters printed in JSON (eg. £ displayed as \u00a3)

- Possibly a separate project - churn out lots of summary data for NotebookLM idea.

## Project Structure

```
OnePulse_Automation/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── run_main.sh              # Shell script to run the application
├── src/                     # Source code
│   ├── __init__.py
│   ├── main.py              # Data processing and chart generation
│   ├── data_loader.py       # File loading utilities
│   ├── data_processor.py    # Data processing logic
│   ├── ppt_generator.py     # PowerPoint generation
│   ├── config.py            # Configuration settings
│   ├── audience_segments.json  # Audience definitions
│   ├── prebuilt_templates.json # Pre-built template configurations
│   └── templates/           # PowerPoint templates
│       └── template.pptx    # Main presentation template
├── tests/                   # Test suite
│   ├── test_data_processing.py  # Tests for data loading and processing
│   ├── test_imports.py      # Import tests
│   ├── test_prebuilt_templates.py # Template tests
│   ├── test_template_matching.py # Template matching tests
│   └── data/                # Test data files
│       ├── test.csv         # Test CSV data
│       ├── test.txt         # Test text data
│       └── test.xlsx        # Test Excel data
├── debug/                   # Debug notebooks and scripts
├── charts/                  # Generated chart images (if any)
├── exports/                 # Generated PowerPoint files (gitignored)
├── Powerpoint Outputs/      # PowerPoint exports (gitignored)
└── survey_data/             # Survey data files (gitignored)
```

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Git
- VS Code (recommended)
- GitHub account with access to the repository

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd OnePulse_Automation
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

   Or use the provided shell script:
   ```bash
   ./run_main.sh
   ```

## Usage

1. Run the application `streamlit run app.py`
2. Upload your survey data file (CSV, JSON, or XLSX) from the `survey_data/` folder
3. Add any audience segments
4. Click "Generate, Save and Run" to create the PowerPoint presentation
5. Check the overview of data (eg. Do your audience segments appear? Do sample sizes look as expected?)
6. Download the generated presentation (saved to `Powerpoint Outputs/` folder)

### File Formats

The application assumes you are uploading unmodified OnePulse exports of respondent level data, in either CSV or XLSX file formats.

### Notes

- Column headers should be on the 4th row
- A "Bank(s)" column (containing semicolon-delimited lists of banks the respondent uses) will be automatically processed into separate columns
- Generated PowerPoint files will be saved to the `Powerpoint Outputs/` folder
- Pre-defined segments are built based on the `prebuilt_templates.json` file
- Survey data files should be placed in the `survey_data/` folder for organization

## Testing

The project uses Python's built-in `unittest` framework for testing. The tests are organized in the `tests/` directory and cover data loading, data processing, and PowerPoint generation functionality.

### Running Tests

To run all tests:
```bash
python -m pytest tests/ -v
```

To run a specific test file:
```bash
python -m pytest tests/test_data_processing.py -v
```

The `-v` flag provides verbose output showing each test case and its result.

### Understanding Test Results

The test output will show:
- A list of all test cases run
- For each test:
  - ✅ `PASSED` if the test passed
  - ❌ Details of what went wrong if the test failed
- A summary showing:
  - Total number of tests run
  - Any failures or errors
  - Time taken to run tests 

Example output:
```
test_csv_loading (tests.test_data_processing.TestDataLoading) ... PASSED
test_xlsx_loading (tests.test_data_processing.TestDataLoading) ... PASSED
test_process_data (tests.test_data_processing.TestDataProcessing) ... PASSED

================================================================================
76 passed in 2.34s
```

### Test Data

Test data files should be placed in the `tests/data/` directory. Currently, the tests expect:
- `test.xlsx`: Sample Excel file for testing XLSX loading
- `test.csv`: Sample CSV file for testing CSV loading

These files should follow the same format as real data files, including having headers on row 4.
