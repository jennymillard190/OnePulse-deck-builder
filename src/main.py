#!/usr/bin/env python3

import os
import pandas as pd
import json
import sys
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
import logging
from typing import Dict, List, Tuple, Optional
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Suppress all debug logs
logging.getLogger('src.data_loader').setLevel(logging.WARNING)
logging.getLogger('src.data_processor').setLevel(logging.WARNING)
logging.getLogger('src.ppt_generator').setLevel(logging.WARNING)

# Add the project root to the Python path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src import config
from src.data_processor import (
    process_raw_audience_data, 
    get_combined_data_from_audiences,
    identify_open_ended_questions
)
from src.ppt_generator import generate_presentation
from src.data_loader import load_file
def normalize_column_name(col_name):
    """
    Normalize column names for comparison by:
    1. Converting to lowercase
    2. Replacing curly quotes with straight quotes
    3. Normalizing whitespace
    4. Removing any BOM or special characters
    """
    if not isinstance(col_name, str):
        return str(col_name)
    
    # Replace curly quotes with straight quotes
    col_name = col_name.replace('"', '"').replace('"', '"')
    col_name = col_name.replace(''', "'").replace(''', "'")
    
    # Normalize whitespace and convert to lowercase
    col_name = ' '.join(col_name.lower().split())
    
    return col_name

def apply_audience_filter(df, definition):
    """
    Apply an audience filter to the dataframe.
    Supports nested AND/OR logic.
    """
    if not definition:
        return pd.Series([True] * len(df))
    
    if isinstance(definition, dict):
        if "AND" in definition:
            masks = [apply_audience_filter(df, cond) for cond in definition["AND"]]
            return pd.concat(masks, axis=1).all(axis=1)
        elif "OR" in definition:
            masks = [apply_audience_filter(df, cond) for cond in definition["OR"]]
            return pd.concat(masks, axis=1).any(axis=1)
        else:
            # Simple case: {column: [values]} or {column: value}
            mask = pd.Series([True] * len(df))
            for column, values in definition.items():
                matching_cols = [col for col in df.columns if col.lower().replace(' ', '_') == column.lower().replace(' ', '_')]
                if not matching_cols:
                    continue
                col = matching_cols[0]
                if df[col].dtype == bool or col.endswith('_customer'):
                    if isinstance(values, list):
                        bool_values = [v if isinstance(v, bool) else v.lower() == 'true' for v in values]
                        mask &= df[col].isin(bool_values)
                    else:
                        bool_value = values if isinstance(values, bool) else values.lower() == 'true'
                        mask &= df[col] == bool_value
                # Handle numeric columns specially (like Age range)
                elif pd.api.types.is_numeric_dtype(df[col].dtype):
                    if isinstance(values, list):
                        # Convert string values to numbers for comparison
                        try:
                            numeric_values = [int(v) if isinstance(v, str) else v for v in values]
                            mask &= df[col].isin(numeric_values)
                        except (ValueError, TypeError):
                            # Fall back to original values if conversion fails
                            mask &= df[col].isin(values)
                    else:
                        # Single value case
                        try:
                            numeric_value = int(values) if isinstance(values, str) else values
                            mask &= df[col] == numeric_value
                        except (ValueError, TypeError):
                            # Fall back to original value if conversion fails
                            mask &= df[col] == values
                else:
                    if isinstance(values, list):
                        mask &= df[col].isin(values)
                    else:
                        mask &= df[col] == values
            return mask
    else:
        raise ValueError("Invalid audience definition")

def process_data(raw_df, audience_defs=None):
    """
    Process the raw data and return the processed data for presentation generation.
    Returns:
        raw_audience_data, combined_data, group_audience_names
    """
    logger.info("\n=== Data Processing Started ===")
    logger.info(f"Loaded spreadsheet with {len(raw_df)} total respondents")
        # Filter out screened-out respondents (only for branching pulses where Q1 is Yes/No)
    q1_col = [col for col in raw_df.columns if col.startswith('Q(1)') and 'Comments' not in col]
    if q1_col:
        q1_values = raw_df[q1_col[0]].astype(str).str.strip().str.lower().unique()
        is_yes_no = set(q1_values) <= {'yes', 'no', 'nan', ''}
        if is_yes_no:
            has_answers = raw_df[q1_col[0]].astype(str).str.strip().str.lower() == 'yes'
            raw_df = raw_df[has_answers].reset_index(drop=True)
            logger.info(f"After filtering screened respondents: {len(raw_df)} respondents")
        else:
            logger.info(f"Non-branching pulse detected - keeping all {len(raw_df)} respondents")
    # Load audience definitions from JSON file if not provided
    if audience_defs is None:
        segments_file_path = os.path.join(os.path.dirname(__file__), "audience_segments.json")
        with open(segments_file_path) as f:
            audience_defs = json.load(f)

    # Extract audience groups if they exist
    audience_groups = audience_defs.pop("__groups__", []) if isinstance(audience_defs, dict) else []

    logger.info("\nProcessing audiences:")
    audience_dfs = {}
    for name, definition in audience_defs.items():
        mask = apply_audience_filter(raw_df, definition)
        audience_dfs[name] = raw_df[mask]
        logger.info(f"{name}: {audience_dfs[name].shape[0]} respondents")

    # Process all questions in the raw data
    logger.info("\nProcessing questions:")
    results = process_raw_audience_data(raw_df)
    
    # Convert results to the expected format for generate_presentation
    raw_audience_data = []
    combined_data = []
    
    # Initialize group_audience_names outside the loop to avoid UnboundLocalError
    group_audience_names = set()
    for group in audience_groups:
        group_audience_names.update(group["audiences"])
    
    for question_id, question_text, categories, values in results:
        if not categories or not values:
            continue
        
        # Build all segments: Total + all audience segments (regardless of group)
        segments = [("Total", values, len(raw_df))]
        segment_name_to_segment = {"Total": ("Total", values, len(raw_df))}
        for name, df in audience_dfs.items():
            if len(df) == 0:
                continue
            audience_values = process_question_for_audience(df, question_id, categories)
            if audience_values:
                seg = (name, audience_values, len(df))
                segments.append(seg)
                segment_name_to_segment[name] = seg
        
        # Add the raw data version (Total only)
        raw_audience_data.append((question_text, categories, [segments[0]]))
        
        # --- Audience Group Logic ---
        # 1. Chart for Total + all segments (grouped and non-grouped)
        if len(segments) > 1:
            combined_data.append((question_text, categories, segments))
        
        # 2. For each group, chart for Total + all group members (if group has at least one member)
        for group in audience_groups:
            group_segments = [segments[0]]
            for audience_name in group["audiences"]:
                if audience_name in segment_name_to_segment:
                    group_segments.append(segment_name_to_segment[audience_name])
            if len(group_segments) > 1:
                combined_data.append((f"{question_text} - {group['name']}", categories, group_segments))
        
        # 3. For each segment not in any group, chart for Total + that segment only
        # BUT: Skip this if there's only one audience and no groups (to avoid duplicates)
        non_grouped_audiences = [name for name in audience_dfs if name not in group_audience_names and name in segment_name_to_segment]
        if len(non_grouped_audiences) > 1 or (len(non_grouped_audiences) == 1 and len(audience_groups) > 0):
            # Only create individual charts if:
            # - There are multiple non-grouped audiences, OR
            # - There's one non-grouped audience but there are also groups (mixed scenario)
            for name in non_grouped_audiences:
                combined_data.append((f"{question_text} ({name})", categories, [segments[0], segment_name_to_segment[name]]))
    
    # Return the set of all grouped audience names as a third value
    return raw_audience_data, combined_data, group_audience_names

def process_question_for_audience(df, question_id, categories):
    """
    Process a single question for a specific audience DataFrame.
    Args:
        df: DataFrame containing only the audience's responses
        question_id: Question ID (as a string)
        categories: List of response categories
    Returns:
        List of values (percentages) for each category
    """
    # Check if this is a multi-select question
    is_multi = any(col.startswith(f'Q({question_id}_') for col in df.columns)
    if is_multi:
        return process_multi_select_question(df, question_id, categories)
    else:
        return process_single_select_question(df, question_id, categories)

def process_multi_select_question(df, question_id, categories):
    """Process a multi-select question for the given DataFrame."""
    values = []
    for cat in categories:
        # Find the column for this category
        cols = [col for col in df.columns if f'Q({question_id}_' in col and cat in col]
        if cols:
            # Sum True values and divide by total responses
            col = cols[0]
            count = df[col].sum()
            pct = count / len(df) if len(df) > 0 else 0
            values.append(pct)
        else:
            values.append(0)
    return values

def process_single_select_question(df, question_id, categories):
    """Process a single-select question for the given DataFrame."""
    values = []
    # Find the question column
    q_col = next((col for col in df.columns if f'Q({question_id})' in col), None)
    if not q_col:
        return None
        
    # Count responses for each category
    response_counts = df[q_col].value_counts()
    total_responses = len(df)
    
    for cat in categories:
        count = response_counts.get(cat, 0)
        pct = count / total_responses if total_responses > 0 else 0
        values.append(pct)
    
    return values


def main():
    # Load data from environment variable
    data_file = os.environ.get('DATA_FILE')
    if not data_file:
        logger.error("No data file specified. Please upload a file through the Streamlit interface.")
        sys.exit(1)

    # Load and process the data file
    raw_df = load_file(data_file)

    logger.info(f"Raw data shape: {raw_df.shape if raw_df is not None else 'None'}")

    # Process the data
    raw_audience_data, combined_data, group_audience_names = process_data(raw_df)

    # Now call the PPT generator
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(config.DEFAULT_OUTPUT_PPTX)
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate the presentation
        generate_presentation(
            raw_audience_data,
            combined_data,
            group_audience_names=group_audience_names
        )
        
        # Verify the file was created
        if os.path.exists(config.DEFAULT_OUTPUT_PPTX):
            logger.info(f"Successfully created presentation at: {config.DEFAULT_OUTPUT_PPTX}")
        else:
            logger.warning(f"Warning: Presentation file was not created at: {config.DEFAULT_OUTPUT_PPTX}")
            
    except Exception as e:
        logger.error(f"Error generating presentation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 