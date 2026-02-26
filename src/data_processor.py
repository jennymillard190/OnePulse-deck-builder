import re
from typing import List, Tuple, Dict, Optional
import pandas as pd
from . import config
import logging

logger = logging.getLogger(__name__)

def compute_segment_values(
    raw_df: pd.DataFrame,
    cats: List[str],
    is_multi: bool,
    key: str
) -> Tuple[List[float], int]:
    """
    Filter raw_df by key and compute proportions for categories.
    
    Args:
        raw_df: DataFrame containing raw survey data
        cats: List of category names
        is_multi: Whether this is a multi-select question
        key: Filter key in format "column:value" or "column:value1,value2"
    
    Returns:
        Tuple containing:
        - List of proportion values for each category
        - Number of respondents in the segment
    """
    base = re.sub(r"\s*\[[^\]]+\]\s*$", "", key).strip()
    df_seg = raw_df.copy()
    
    # Apply filters
    for part in [p.strip() for p in base.split('/')]:
        if ':' not in part:
            continue
        col, val = [x.strip() for x in part.split(':', 1)]
        opts = [v.strip() for v in val.split(',')]
        df_seg = df_seg[df_seg[col].isin(opts)]
    
    n_resp = len(df_seg)
    vals = [0.0] * len(cats)
    
    if n_resp:
        if is_multi:
            # Handle multi-select questions
            # Find the first multi-select column to get the question ID
            multi_col = next((c for c in df_seg.columns if re.match(r'Q\(\d+_\d+\)', c)), None)
            if multi_col:
                q_id = re.search(r'Q\(\d+\)', multi_col).group(0)
                q_cols = [c for c in df_seg.columns if c.startswith(q_id.replace(')', '_'))]
                for idx, cat in enumerate(cats):
                    col = next((c for c in q_cols if cat in c), None)
                    vals[idx] = df_seg[col].notna().sum() / n_resp if col else 0.0
        else:
            # Handle single-select questions
            # Find the first single-select column to get the question ID
            single_col = next((c for c in df_seg.columns if re.match(r'Q\(\d+\)', c) and '_' not in c and 'Comments' not in c), None)
            if single_col:
                q_id = re.search(r'Q\(\d+\)', single_col).group(0)
                q_col = next((c for c in df_seg.columns if c.startswith(q_id) and '_' not in c and 'Comments' not in c), None)
                if q_col:
                    for idx, cat in enumerate(cats):
                        vals[idx] = (df_seg[q_col] == cat).sum() / n_resp
                    
    return vals, n_resp

def get_raw_audience_data(
    raw_df: pd.DataFrame,
    summary_data: Dict[str, Tuple[List[str], List[float]]],
    summary_counts: Dict[str, int],
    mapping: pd.DataFrame
) -> List[Tuple[str, List[Tuple[str, List[float], int]]]]:
    """
    Process raw audience data for chart generation.
    
    Args:
        raw_df: DataFrame containing raw survey data
        summary_data: Dictionary mapping titles to (categories, values) tuples
        summary_counts: Dictionary mapping titles to total counts
        mapping: DataFrame containing mapping information
    
    Returns:
        List of tuples containing:
        - Chart title
        - List of (label, values, count) tuples for each segment
    """
    raw_map = mapping[
        (mapping.type.str.strip().str.lower() == 'raw') &
        (~mapping.key.str.strip().str.lower().str.startswith('chart combining'))
    ]
    
    results = []
    for title, (cats, totals) in summary_data.items():
        is_multi = 'select all that apply' in title.lower()
        segments = []
        
        for _, row in raw_map.iterrows():
            key = str(row.key)
            m = re.search(r"\[([^\]]+)\]", key)
            label = m.group(1) if m else key
            vals, n_resp = compute_segment_values(raw_df, cats, is_multi, key)
            segments.append((label, vals, n_resp))
            
        results.append((title, segments))
        
    return results

def get_combined_data_from_audiences(raw_df, results, audience_dfs):
    """
    Build combined_data using the new audience_dfs (from JSON).
    results: output of process_raw_audience_data(raw_df)
    audience_dfs: dict of {audience_name: filtered DataFrame}
    """
    combined_data = []
    for q_id, categories, _ in results:
        # Get the question title
        q_cols = [col for col in raw_df.columns if f"Q({q_id}" in col and 'Comments' not in col]
        if q_cols:
            try:
                # For multi-select questions, the format is "Q(3_1) Response[Question: ...]"
                # For single-select questions, the format is "Q(2) Question text here"
                if '_' in q_cols[0]:  # Multi-select question
                    # Extract the part between [Question: and ]
                    question_text = q_cols[0].split('[Question:', 1)[1].rstrip(']')
                else:  # Single-select question
                    # Split on the first closing parenthesis and take everything after it
                    question_text = q_cols[0].split(')', 1)[1].strip()
                title = question_text
            except IndexError:
                title = q_cols[0]
        else:
            title = f"Q{q_id}"

        segments = []
        for audience_name, audience_df in audience_dfs.items():
            # Skip empty audiences
            if len(audience_df) == 0:
                continue
                
            # Determine question type
            is_multi = any(col.startswith(f'Q({q_id}_') for col in audience_df.columns)
            
            # Get values using our processing functions
            if is_multi:
                values = process_multi_select_question(audience_df, q_id, categories)
            else:
                values = process_single_select_question(audience_df, q_id, categories)
            
            if values:
                segments.append((audience_name, values, len(audience_df)))

        # Add the 'Total' segment (from the full raw_df)
        is_multi = any(col.startswith(f'Q({q_id}_') for col in raw_df.columns)
        if is_multi:
            total_values = process_multi_select_question(raw_df, q_id, categories)
        else:
            total_values = process_single_select_question(raw_df, q_id, categories)
        
        if total_values:
            segments.insert(0, ("Total", total_values, len(raw_df)))

        combined_data.append((title, categories, segments))
    return combined_data

def identify_question_type(df, question_id):
    """
    Identify if a question is single-select or multi-select based on column patterns.
    Also identifies any comment columns.
    """
    multi_select_cols = [col for col in df.columns if col.startswith(f'Q({question_id}_')]
    single_select_col = next((col for col in df.columns if f'Q({question_id})' in col and '_' not in col), None)
    comment_cols = [col for col in df.columns if f'Q({question_id}) Comments' in col]
    if multi_select_cols:
        return 'multi_select', multi_select_cols, comment_cols
    elif single_select_col:
        return 'single_select', [single_select_col], comment_cols
    else:
        return None, [], []

def extract_categories_from_columns(df, question_id, is_multi_select):
    """
    Extract category names from column headers.
    For single-select: gets unique values in the main column
    For multi-select: extracts category names from column headers, stripping out the 'Q(1_1)' prefix.
    """
    if is_multi_select:
        cols = [col for col in df.columns if col.startswith(f'Q({question_id}_')]
        categories = []
        for col in cols:
            try:
                # Extract the part before the first '[', then strip out the 'Q(1_1)' prefix
                label = col.split('[', 1)[0].strip()
                # Remove the 'Q(1_1)' prefix if present
                if label.startswith(f'Q({question_id}_'):
                    label = label.split(')', 1)[1].strip()
                categories.append(label)
            except IndexError:
                categories.append(col)  # fallback: use the whole column name
        return categories
    else:
        main_col = next((col for col in df.columns if f'Q({question_id})' in col and '_' not in col), None)
        if main_col:
            # Handle both list and non-list values
            all_values = set()
            for val in df[main_col].dropna():
                if isinstance(val, list):
                    all_values.update(val)
                else:
                    all_values.add(val)
            categories = sorted(list(all_values))
        else:
            categories = []
        return categories

def process_single_select_question(df, question_id, categories):
    """
    Process a single-select question.
    """
    main_col = next((col for col in df.columns if f'Q({question_id})' in col and '_' not in col), None)
    if not main_col:
        return None
    
    logger.debug(f"Processing single-select question {question_id}")
    
    values = []
    total_responses = 0
    for category in categories:
        # Handle both list and non-list values
        count = sum(1 for val in df[main_col] if (isinstance(val, list) and category in val) or val == category)
        values.append(count)
        total_responses += count
    
    # Convert to percentages if we have responses
    if total_responses > 0:
        values = [v / total_responses for v in values]
    return values

def process_multi_select_question(df, question_id, categories):
    """
    Process a multi-select question.
    """
    question_cols = [col for col in df.columns if col.startswith(f'Q({question_id}_')]
    if not question_cols:
        return None

    # Create a mapping of category to column
    category_to_col = {}
    for col in question_cols:
        try:
            # Extract the part before the first '[', then strip out the 'Q(1_1)' prefix
            label = col.split('[', 1)[0].strip()
            # Remove the 'Q(1_1)' prefix if present
            if label.startswith(f'Q({question_id}_'):
                label = label.split(')', 1)[1].strip()
            category_to_col[label] = col
        except IndexError:
            # If we can't parse the column name, use it as is
            category_to_col[col] = col

    values = []
    total_respondents = len(df)

    for category in categories:
        col = category_to_col.get(category)
        if col:
            # Count TRUE values (respondents who selected this option)
            count = df[col].sum()
            percentage = count / total_respondents
            values.append(percentage)
        else:
            values.append(0.0)

    return values

def process_raw_audience_data(raw_df):
    """
    Process all questions in the dataframe and return a list of (question_id, categories, values).
    Now sorts categories and values in descending order of value.
    """
    # Find all unique question IDs
    question_ids = set()
    for col in raw_df.columns:
        if 'Q(' in col:
            q_id = col.split('(')[1].split(')')[0].split('_')[0]
            question_ids.add(q_id)
    logger.debug(f"Found {len(question_ids)} questions to process")

    # Identify open-ended questions
    open_ended_questions = identify_open_ended_questions(raw_df)
    
    # Only mark a question as open-ended if the main response columns (not comment columns) are open-ended
    open_ended_ids = set()
    for col in open_ended_questions:
        q_id = col.split('(')[1].split(')')[0].split('_')[0]
        
        # Check if this is a comment column
        is_comment = 'Comments' in col
        
        if not is_comment:
            # Only mark as open-ended if it's not a comment column
            open_ended_ids.add(q_id)
        else:
            # For comment columns, check if the main question columns are also open-ended
            # If the main question has valid response columns, don't skip it
            main_cols = [c for c in raw_df.columns if f'Q({q_id}' in c and 'Comments' not in c]
            if not main_cols:
                # No main response columns, so this is truly an open-ended question
                open_ended_ids.add(q_id)
    
    logger.debug(f"Found {len(open_ended_ids)} open-ended questions")

    results = []
    for q_id in sorted(question_ids):
        # Skip open-ended questions
        if q_id in open_ended_ids:
            logger.debug(f"Skipping open-ended question {q_id}")
            continue

        q_type, cols, comment_cols = identify_question_type(raw_df, q_id)
        if q_type:
            # Extract question text from the first column
            question_text = cols[0].split('[', 1)[1].rstrip(']') if '[' in cols[0] else cols[0]
            logger.debug(f"Processing question {q_id}: {question_text}")
            
            categories = extract_categories_from_columns(raw_df, q_id, q_type == 'multi_select')
            
            if q_type == 'single_select':
                values = process_single_select_question(raw_df, q_id, categories)
            else:
                values = process_multi_select_question(raw_df, q_id, categories)
            
            if values:
                # Sort categories and values by values in descending order
                sorted_pairs = sorted(zip(categories, values), key=lambda x: x[1], reverse=True)
                categories, values = zip(*sorted_pairs)
                categories = list(categories)
                values = list(values)
                results.append((q_id, question_text, categories, values))
    
    return results

def identify_open_ended_questions(df: pd.DataFrame) -> List[str]:
    """
    Identify open-ended questions in the dataset based on response patterns.
    
    Args:
        df: DataFrame containing the survey data
    
    Returns:
        List of column names that appear to be open-ended questions
    """
    open_ended_columns = []
    
    # Common multiple-choice patterns
    common_patterns = [
        r'^(yes|no)$',
        r'^(agree|disagree|neutral)$',
        r'^(strongly agree|agree|neutral|disagree|strongly disagree)$',
        r'^(very likely|likely|neutral|unlikely|very unlikely)$',
        r'^(excellent|good|fair|poor)$',
        r'^(always|often|sometimes|rarely|never)$',
        r'^(true|false)$',
        r'^(none of these|don\'t know)$'
    ]
    
    for column in df.columns:
        # Skip non-question columns
        if not column.startswith('Q('):
            continue
            
        # Get non-null responses
        responses = df[column].dropna()
        if len(responses) == 0:
            continue
            
        # Convert all responses to lowercase for pattern matching
        responses_lower = responses.astype(str).str.lower()
        
        # Calculate metrics
        total_responses = len(responses)
        unique_responses = len(responses.unique())
        unique_ratio = unique_responses / total_responses
        
        # Calculate average response length
        avg_length = responses.astype(str).str.len().mean()
        
        # Check if responses match common multiple-choice patterns
        matches_pattern = False
        for pattern in common_patterns:
            if responses_lower.str.match(pattern).all():
                matches_pattern = True
                break
        
        # Identify as open-ended if:
        # 1. High number of unique responses (>20)
        # 2. High ratio of unique to total responses (>0.5)
        # 3. Average response length is significant (>20 characters)
        # 4. Doesn't match common multiple-choice patterns
        if (unique_responses > 20 and 
            unique_ratio > 0.5 and 
            avg_length > 20 and 
            not matches_pattern):
            
            logger.info(f"\nPotential open-ended question found: {column}")
            logger.info(f"Total responses: {total_responses}")
            logger.info(f"Unique responses: {unique_responses}")
            logger.info(f"Unique ratio: {unique_ratio:.2%}")
            logger.info(f"Average response length: {avg_length:.1f} characters")
            logger.info("Sample responses:")
            for resp in responses.unique()[:5]:  # Show first 5 unique responses
                logger.info(f"  - {resp}")
            
            open_ended_columns.append(column)
    
    return open_ended_columns