#!/bin/bash
set -x  # Print commands and their arguments as they are executed
echo "Debug: Starting shell script"
echo "Debug: PYTHONPATH=$PYTHONPATH"
echo "Debug: DATA_FILE=$DATA_FILE"
echo "Debug: Current directory: $(pwd)"
echo "Debug: Python executable: /Users/sthompso/.pyenv/versions/3.13.2/bin/python3.13"
echo "Debug: Main script: /Users/sthompso/Library/CloudStorage/OneDrive-PublicisGroupe/Projects/OnePulse Charting (Jen)/2025-05-21/OnePulse_Automation/src/main.py"

export PYTHONPATH="/Users/sthompso/Library/CloudStorage/OneDrive-PublicisGroupe/Projects/OnePulse Charting (Jen)/2025-05-21/OnePulse_Automation"
export DATA_FILE="/Users/sthompso/Library/CloudStorage/OneDrive-PublicisGroupe/Projects/OnePulse Charting (Jen)/2025-05-21/OnePulse_Automation/temp_data.csv"

echo "Debug: Running main.py..."
"/Users/sthompso/.pyenv/versions/3.13.2/bin/python3.13" "/Users/sthompso/Library/CloudStorage/OneDrive-PublicisGroupe/Projects/OnePulse Charting (Jen)/2025-05-21/OnePulse_Automation/src/main.py" 2>&1
exit_code=$?
echo "Debug: main.py completed with exit code $exit_code"
exit $exit_code
