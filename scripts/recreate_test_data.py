#!/usr/bin/env python3
"""
Recreate the test data Excel file.
"""

import os
import pandas as pd

# Get project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Recreate the test data Excel file."""
    print("Loading test CSV data...")
    
    # Load the test CSV file, skipping the first 3 rows which are metadata
    test_csv_path = os.path.join(project_root, "tests", "data", "test.csv")
    df = pd.read_csv(test_csv_path, skiprows=3)
    
    # Export to Excel
    output_file = os.path.join(project_root, "survey_data", "test_data_for_app.xlsx")
    print(f"Exporting to {output_file}...")
    
    df.to_excel(output_file, index=False)
    
    print(f"✅ Test data exported to {output_file}")
    print(f"📊 DataFrame shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")

if __name__ == "__main__":
    main() 