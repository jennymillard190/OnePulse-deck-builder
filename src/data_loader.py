import os
import glob
import pandas as pd
import numpy as np
import re
from typing import Optional, Tuple, Dict, List, Any
from . import config

def find_latest_export(suffix: Optional[str] = None) -> Optional[str]:
    """
    Find the most recent Excel file in the exports directory.
    
    Args:
        suffix: Optional suffix to filter files (e.g., 'summary' or 'raw')
    
    Returns:
        Path to the latest matching Excel file, or None if no files found
    """
    if not os.path.isdir(config.EXPORTS_DIR):
        return None
    pattern = f"*_{suffix}*.xls*" if suffix else "*.xls*"
    files = [f for f in glob.glob(os.path.join(config.EXPORTS_DIR, pattern))
             if not os.path.basename(f).startswith("~$")]
    return max(files, key=os.path.getmtime) if files else None

def load_summary_data() -> Tuple[Dict[str, Tuple[List[str], List[float]]], Dict[str, int]]:
    """
    Load and process summary data from the latest summary Excel file.
    
    Returns:
        Tuple containing:
        - Dictionary mapping titles to (categories, values) tuples
        - Dictionary mapping titles to total counts
    """
    summary_data: Dict[str, Tuple[List[str], List[float]]] = {}
    summary_counts: Dict[str, int] = {}
    
    summary_file = find_latest_export('summary')
    if not summary_file:
        return summary_data, summary_counts
        
    xls = pd.ExcelFile(summary_file)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet, header=None)
        rows, cols = df.shape
        hits = []
        
        # Find 'Total' cells and their counts
        for r in range(rows-1):
            for c in range(cols):
                if str(df.iat[r,c]).strip().lower() == 'total':
                    try:
                        cnt = float(df.iat[r+1,c])
                    except:
                        continue
                    if 1 <= cnt <= 10000:
                        hits.append((r,c,int(cnt)))
        
        # Keep only the leftmost 'Total' for each row
        uniq = {}
        for r,c,cnt in hits:
            if r not in uniq or c < uniq[r][1]:
                uniq[r] = (r,c,cnt)
                
        # Process each unique 'Total' row
        for r,c,total_n in uniq.values():
            # Get category labels
            labels = []
            for c2 in range(c+1, cols):
                v = df.iat[r,c2]
                if pd.isna(v) or not str(v).strip():
                    break
                labels.append(str(v).strip())
                
            if not labels:
                continue
                
            # Get values for each category
            vals, ok = [], True
            for i, lab in enumerate(labels):
                rv = df.iat[r+1,c+1+i]
                try:
                    num = float(rv)
                    if num > 1:
                        num /= total_n
                except:
                    txt = str(rv).strip()
                    if txt.endswith('%'):
                        try:
                            num = float(txt.rstrip('%'))/100
                        except:
                            ok = False
                    else:
                        ok = False
                if not ok or pd.isna(num) or np.isinf(num):
                    ok = False
                    break
                vals.append(num)
                
            if not ok:
                continue
                
            # Sort categories by value
            cats, nums = zip(*sorted(zip(labels, vals), key=lambda x: x[1], reverse=True))
            
            # Get title from the first non-empty cell above
            title = next(
                (df.iat[rt,0].strip() for rt in range(r-1,-1,-1)
                 if isinstance(df.iat[rt,0],str) and df.iat[rt,0].strip()),
                sheet
            )
            
            summary_data[title] = (list(cats), list(nums))
            summary_counts[title] = total_n
            
    return summary_data, summary_counts

def load_raw_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load raw data and mapping from the latest raw Excel file.
    
    Returns:
        Tuple containing:
        - Raw data DataFrame
        - Mapping DataFrame
    """
    raw_file = find_latest_export('raw')
    if not raw_file:
        return None, None
        
    # Load mapping sheet
    mapping = pd.read_excel(raw_file, sheet_name=1, header=None,
                          usecols=[0,1], names=['key','type']).dropna()
    
    # Load main data sheet
    full = pd.read_excel(raw_file, sheet_name=0, header=None)
    hdr_i = full.index[full.iloc[:,0].astype(str).str.strip()=='User ID'][0]
    raw_df = full.iloc[hdr_i+1:].reset_index(drop=True)
    raw_df.columns = full.iloc[hdr_i].astype(str).str.strip()
    
    return raw_df, mapping 

def process_semicolon_separated_column(df: pd.DataFrame, column_name: str, suffix_pattern: str) -> pd.DataFrame:
    """
    Process a semicolon-separated column into individual boolean columns.
    
    Args:
        df: DataFrame to process
        column_name: Name of the column to process
        suffix_pattern: Pattern for naming new columns (e.g., "_customer" or "_child")
        
    Returns:
        DataFrame with new boolean columns added
    """
    if column_name not in df.columns:
        return df
    
    # Get all unique values from the semicolon-separated lists
    all_values = set()
    for values_str in df[column_name].dropna():
        values = [value.strip() for value in values_str.split(';')]
        all_values.update(values)
    
    # Sort values if this is an age of children column
    if column_name == 'Age of children':
        # Define the correct age order
        age_order = [
            '0-3 months',
            '4-7 months', 
            '8-11 months',
            '1-2 years',
            '3-4 years',
            '5-6 years',
            '7-8 years',
            '9-10 years',
            '11-12 years',
            '13-14 years',
            '15-16 years',
            '17-18 years',
            '19+ years'
        ]
        # Sort values according to the age order, with any unknown values at the end
        sorted_values = []
        for age in age_order:
            if age in all_values:
                sorted_values.append(age)
        # Add any remaining values that weren't in our predefined order
        for value in all_values:
            if value not in sorted_values:
                sorted_values.append(value)
        all_values = sorted_values
    else:
        # For other columns, sort alphabetically by lowercase names
        all_values = sorted(all_values, key=str.lower)
    
    # Create boolean columns for each unique value
    for value in all_values:
        # Skip empty values
        if not value.strip():
            continue
            
        # Create safe column name: replace special characters and spaces
        safe_value = value.lower()
        safe_value = safe_value.replace('-', '_')
        safe_value = safe_value.replace('+', '_plus')
        safe_value = safe_value.replace(' ', '_')
        
        # Apply the suffix pattern
        if suffix_pattern == "_customer":
            # For banks, use the existing pattern
            new_column_name = f"{safe_value}{suffix_pattern}"
        else:
            # For other columns, use "has_" prefix
            new_column_name = f"has_{safe_value}{suffix_pattern}"
        
        # Create boolean column
        df[new_column_name] = df[column_name].fillna('').str.contains(value, regex=False)
    
    return df

def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process a DataFrame according to our application's rules.
    
    Args:
        df: DataFrame to process
        
    Returns:
        Processed DataFrame
    """
    # Process column names
    df.columns = (
        df.columns
          .str.strip()
          .str.replace(r"\s+", " ", regex=True)
    )
    
    # Process bank columns
    df = process_semicolon_separated_column(df, 'Bank(s)', '_customer')
    
    # Process age of children columns
    df = process_semicolon_separated_column(df, 'Age of children', '_child')
    
    # Process multi-select questions
    for col in df.columns:
        if df[col].dtype == object and col not in ['Bank(s)', 'Age of children'] and re.match(r'Q\(\d+_\d+\)', col):
            # Extract the expected value from the column name (the part before [Question:)
            expected_value = col.split('[', 1)[0].split(')', 1)[1].strip()
            # Convert to boolean: TRUE if the cell contains the expected value, FALSE otherwise
            df[col] = df[col].fillna('').astype(str).str.contains(expected_value, regex=False)
    
    return df

def load_file(file_path: str) -> pd.DataFrame:
    """
    Load a data file (CSV, JSON, or XLSX) and process it according to our application's rules.
    
    Args:
        file_path: Path to the file to load
        
    Returns:
        Processed DataFrame
        
    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file type is not supported
    """
    # Check file type first
    lower_path = file_path.lower()
    if not (lower_path.endswith('.csv') or 
            lower_path.endswith('.json') or 
            lower_path.endswith('.xlsx') or 
            lower_path.endswith('.xls')):
        raise ValueError(f"Unsupported file type. File must be CSV, JSON, or Excel (XLSX/XLS)")
    
    # Then check file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Load the file based on extension
    if lower_path.endswith('.csv'):
        df = pd.read_csv(file_path, skiprows=3)
    elif lower_path.endswith('.json'):
        df = pd.read_json(file_path)
    else:
        df = pd.read_excel(file_path, sheet_name=0, skiprows=3)
    
    return process_dataframe(df)

def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    """
    Load a file uploaded through Streamlit and process it.
    
    Args:
        uploaded_file: File object from Streamlit's file_uploader
        
    Returns:
        Processed DataFrame
    """
    # Load the file based on extension
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file, skiprows=3)
    elif uploaded_file.name.lower().endswith('.json'):
        df = pd.read_json(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file, sheet_name=0, skiprows=3)
    
    return process_dataframe(df) 