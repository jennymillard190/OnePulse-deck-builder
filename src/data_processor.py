import re
from typing import List, Tuple, Dict, Optional
import pandas as pd
from . import config
from .scale_helpers import order_scale_categories_and_values
import logging

logger = logging.getLogger(__name__)

def compute_segment_values(
    raw_df: pd.DataFrame,
    cats: List[str],
    is_multi: bool,
    key: str
) -> Tuple[List[float], int]:
    base = re.sub(r"\s*\[[^\]]+\]\s*$", "", key).strip()
    df_seg = raw_df.copy()
    
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
            multi_col = next((c for c in df_seg.columns if re.match(r'Q\(\d+_\d+\)', c)), None)
            if multi_col:
                q_id = re.search(r'Q\(\d+\)', multi_col).group(0)
                q_cols = [c for c in df_seg.columns if c.startswith(q_id.replace(')', '_'))]
                for idx, cat in enumerate(cats):
                    col = next((c for c in q_cols if cat in c), None)
                    # FIX: use .sum() on boolean column, not .notna()
                    vals[idx] = df_seg[col].sum() / n_resp if col else 0.0
        else:
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
    combined_data = []
    for q_id, categories, _ in results:
        q_cols = [col for col in raw_df.columns if f"Q({q_id}" in col and 'Comments' not in col]
        if q_cols:
            try:
                if '_' in q_cols[0]:
                    question_text = q_cols[0].split('[Question:', 1)[1].rstrip(']')
                else:
                    question_text = q_cols[0].split(')', 1)[1].strip()
                title = question_text
            except IndexError:
                title = q_cols[0]
        else:
            title = f"Q{q_id}"

        segments = []
        for audience_name, audience_df in audience_dfs.items():
            if len(audience_df) == 0:
                continue
                
            is_multi = any(col.startswith(f'Q({q_id}_') for col in audience_df.columns)
            
            if is_multi:
                values = process_multi_select_question(audience_df, q_id, categories)
            else:
                values = process_single_select_question(audience_df, q_id, categories)
            
            if values:
                segments.append((audience_name, values, len(audience_df)))

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
    if is_multi_select:
        cols = [col for col in df.columns if col.startswith(f'Q({question_id}_')]
        categories = []
        for col in cols:
            try:
                label = col.split('[', 1)[0].strip()
                if label.startswith(f'Q({question_id}_'):
                    label = label.split(')', 1)[1].strip()
                categories.append(label)
            except IndexError:
                categories.append(col)
        return categories
    else:
        main_col = next((col for col in df.columns if f'Q({question_id})' in col and '_' not in col), None)
        if main_col:
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
    Process a single-select question using only valid respondents for that question.
    """
    main_col = next((col for col in df.columns if f'Q({question_id})' in col and '_' not in col), None)
    if not main_col:
        return None
    
    logger.debug(f"Processing single-select question {question_id}")
    
    valid_responses = df[main_col].dropna()
    total_respondents = len(valid_responses)

    values = []
    for category in categories:
        count = sum(
            1 for val in valid_responses
            if (isinstance(val, list) and category in val) or val == category
        )
        values.append(count / total_respondents if total_respondents > 0 else 0)
    
    return values

def process_multi_select_question(df, question_id, categories):
    """
    Process a multi-select question.
    """
    question_cols = [col for col in df.columns if col.startswith(f'Q({question_id}_')]
    if not question_cols:
        return None

    category_to_col = {}
    for col in question_cols:
        try:
            label = col.split('[', 1)[0].strip()
            if label.startswith(f'Q({question_id}_'):
                label = label.split(')', 1)[1].strip()
            category_to_col[label] = col
        except IndexError:
            category_to_col[col] = col

    values = []
    total_respondents = len(df)

    for category in categories:
        col = category_to_col.get(category)
        if col:
            # FIX: .sum() works correctly on boolean columns after data_loader fix
            count = df[col].sum()
            percentage = count / total_respondents
            values.append(percentage)
        else:
            values.append(0.0)

    return values

def process_raw_audience_data(raw_df):
    """
    Process all questions in the dataframe and return a list of (question_id, question_text, categories, values).
    Sorts categories and values in descending order of value.
    """
    question_ids = set()
    for col in raw_df.columns:
        if 'Q(' in col:
            q_id = col.split('(')[1].split(')')[0].split('_')[0]
            question_ids.add(q_id)
    logger.debug(f"Found {len(question_ids)} questions to process")

    open_ended_questions = identify_open_ended_questions(raw_df)
    
    open_ended_ids = set()
    for col in open_ended_questions:
        q_id = col.split('(')[1].split(')')[0].split('_')[0]
        is_comment = 'Comments' in col
        if not is_comment:
            open_ended_ids.add(q_id)
        else:
            main_cols = [c for c in raw_df.columns if f'Q({q_id}' in c and 'Comments' not in c]
            if not main_cols:
                open_ended_ids.add(q_id)
    
    logger.debug(f"Found {len(open_ended_ids)} open-ended questions")

    results = []
    for q_id in sorted(question_ids):
        if q_id in open_ended_ids:
            logger.debug(f"Skipping open-ended question {q_id}")
            continue

        q_type, cols, comment_cols = identify_question_type(raw_df, q_id)
        if q_type:
            question_text = cols[0].split('[', 1)[1].rstrip(']') if '[' in cols[0] else cols[0]
            logger.debug(f"Processing question {q_id}: {question_text}")
            
            categories = extract_categories_from_columns(raw_df, q_id, q_type == 'multi_select')
            
            if q_type == 'single_select':
                values = process_single_select_question(raw_df, q_id, categories)
            else:
                values = process_multi_select_question(raw_df, q_id, categories)
            
            if values:
                scale_ordered = order_scale_categories_and_values(categories, values)
                if scale_ordered is not None:
                    categories, values = scale_ordered
                else:
                    sorted_pairs = sorted(zip(categories, values), key=lambda x: x[1], reverse=True)
                    categories, values = zip(*sorted_pairs)
                    categories = list(categories)
                    values = list(values)
                results.append((q_id, question_text, categories, values))
    
    return results

def identify_open_ended_questions(df: pd.DataFrame) -> List[str]:
    """
    Identify open-ended questions in the dataset based on response patterns.
    """
    open_ended_columns = []
    
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
        if not column.startswith('Q('):
            continue
            
        responses = df[column].dropna()
        if len(responses) == 0:
            continue
            
        responses_lower = responses.astype(str).str.lower()
        
        total_responses = len(responses)
        unique_responses = len(responses.unique())
        unique_ratio = unique_responses / total_responses
        avg_length = responses.astype(str).str.len().mean()
        
        matches_pattern = False
        for pattern in common_patterns:
            if responses_lower.str.match(pattern).all():
                matches_pattern = True
                break
        
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
            for resp in responses.unique()[:5]:
                logger.info(f"  - {resp}")
            
            open_ended_columns.append(column)
    
    return open_ended_columns
