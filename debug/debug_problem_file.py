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

def debug_problem_file():
    """Debug function to understand why only the first question is processed in the problem file"""
    
    # Load the problem file
    problem_csv = os.path.join(project_root, "survey_data", "Problem_file.csv")
    df = load_file(problem_csv)
    
    print("=== PROBLEM FILE DEBUG ===")
    print(f"DataFrame shape: {df.shape}")
    print(f"Total respondents: {len(df)}")
    
    # Find all question columns
    question_columns = [col for col in df.columns if col.startswith('Q(')]
    print(f"\nFound {len(question_columns)} question columns:")
    for col in question_columns:
        print(f"  - {col}")
    
    # Group by question ID
    question_groups = {}
    for col in question_columns:
        if 'Q(' in col:
            q_id = col.split('(')[1].split(')')[0].split('_')[0]
            if q_id not in question_groups:
                question_groups[q_id] = []
            question_groups[q_id].append(col)
    
    print(f"\n=== QUESTION GROUPS ===")
    for q_id, cols in sorted(question_groups.items()):
        print(f"\nQuestion {q_id}:")
        for col in cols:
            # Count non-empty responses
            responses = df[col].dropna()
            print(f"  - {col}: {len(responses)} responses")
            if len(responses) > 0:
                print(f"    Sample responses: {list(responses.unique())[:3]}")
    
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
    all_q_ids = set(question_groups.keys())
    
    print(f"\n=== QUESTION ID ANALYSIS ===")
    print(f"All question IDs found: {sorted(all_q_ids)}")
    print(f"Processed question IDs: {sorted(processed_q_ids)}")
    print(f"Missing question IDs: {sorted(all_q_ids - processed_q_ids)}")
    
    # Check why questions might be missing
    for q_id in sorted(all_q_ids):
        if q_id not in processed_q_ids:
            print(f"\nAnalyzing missing question {q_id}:")
            q_cols = question_groups[q_id]
            print(f"  Columns: {q_cols}")
            
            # Check if it's open-ended
            is_open_ended = any(col in open_ended_cols for col in q_cols)
            print(f"  Is open-ended: {is_open_ended}")
            
            # Check response patterns for each column
            for col in q_cols:
                responses = df[col].dropna()
                print(f"  {col}: {len(responses)} responses, {len(responses.unique())} unique")
                if len(responses) > 0:
                    print(f"    Sample responses: {list(responses.unique())[:3]}")
                    
                    # Check if responses are boolean (True/False) or text
                    if len(responses) > 0:
                        sample_response = responses.iloc[0]
                        print(f"    Sample response type: {type(sample_response)}, value: {sample_response}")
    
    # Check the data processing logic for each question
    print(f"\n=== DETAILED PROCESSING ANALYSIS ===")
    for q_id in sorted(all_q_ids):
        print(f"\nQuestion {q_id} processing:")
        q_cols = question_groups[q_id]
        
        # Check if it's multi-select or single-select
        multi_select_cols = [col for col in q_cols if '_' in col and col.split('_')[1].split(')')[0].isdigit()]
        single_select_cols = [col for col in q_cols if '_' not in col or not col.split('_')[1].split(')')[0].isdigit()]
        
        print(f"  Multi-select columns: {len(multi_select_cols)}")
        print(f"  Single-select columns: {len(single_select_cols)}")
        
        if multi_select_cols:
            print(f"  Multi-select sample column: {multi_select_cols[0]}")
            sample_col = multi_select_cols[0]
            responses = df[sample_col].dropna()
            if len(responses) > 0:
                sample_response = responses.iloc[0]
                print(f"    Sample response: {sample_response} (type: {type(sample_response)})")
                
                # Check if it's boolean
                if isinstance(sample_response, bool):
                    print(f"    Boolean column detected")
                elif isinstance(sample_response, str):
                    print(f"    String column detected")
                else:
                    print(f"    Other type: {type(sample_response)}")

if __name__ == "__main__":
    debug_problem_file() 