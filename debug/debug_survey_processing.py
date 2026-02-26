#!/usr/bin/env python3

import sys
import os
import pandas as pd

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data_loader import load_file
from src.data_processor import process_raw_audience_data, identify_open_ended_questions

def debug_survey_processing():
    """Debug function to understand survey processing"""
    
    # Load test data
    test_csv = os.path.join(project_root, "tests", "data", "test.csv")
    df = load_file(test_csv)
    
    print("=== SURVEY PROCESSING DEBUG ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Find all question columns
    question_columns = [col for col in df.columns if col.startswith('Q(')]
    print(f"\nFound {len(question_columns)} question columns:")
    for col in question_columns:
        print(f"  - {col}")
    
    # Identify open-ended questions
    open_ended_cols = identify_open_ended_questions(df)
    print(f"\nOpen-ended questions identified: {len(open_ended_cols)}")
    for col in open_ended_cols:
        print(f"  - {col}")
    
    # Process all questions
    print("\n=== PROCESSING ALL QUESTIONS ===")
    results = process_raw_audience_data(df)
    
    print(f"\nProcessed {len(results)} questions:")
    for i, (q_id, question_text, categories, values) in enumerate(results, 1):
        print(f"\nQuestion {i}:")
        print(f"  ID: {q_id}")
        print(f"  Text: {question_text[:100]}...")
        print(f"  Categories: {len(categories)} categories")
        print(f"  Values: {len(values)} values")
        print(f"  Sample categories: {categories[:3]}")
        print(f"  Sample values: {values[:3]}")
    
    # Check for any questions that might be missing
    processed_q_ids = {result[0] for result in results}
    all_q_ids = set()
    for col in question_columns:
        if 'Q(' in col:
            q_id = col.split('(')[1].split(')')[0].split('_')[0]
            all_q_ids.add(q_id)
    
    print(f"\n=== QUESTION ID ANALYSIS ===")
    print(f"All question IDs found: {sorted(all_q_ids)}")
    print(f"Processed question IDs: {sorted(processed_q_ids)}")
    print(f"Missing question IDs: {sorted(all_q_ids - processed_q_ids)}")
    
    # Check why questions might be missing
    for q_id in sorted(all_q_ids):
        if q_id not in processed_q_ids:
            print(f"\nAnalyzing missing question {q_id}:")
            q_cols = [col for col in question_columns if f'Q({q_id}' in col]
            print(f"  Columns: {q_cols}")
            
            # Check if it's open-ended
            is_open_ended = any(col in open_ended_cols for col in q_cols)
            print(f"  Is open-ended: {is_open_ended}")
            
            # Check response patterns
            for col in q_cols[:2]:  # Check first 2 columns
                responses = df[col].dropna()
                print(f"  {col}: {len(responses)} responses, {len(responses.unique())} unique")
                if len(responses) > 0:
                    print(f"    Sample responses: {list(responses.unique())[:3]}")

if __name__ == "__main__":
    debug_survey_processing() 