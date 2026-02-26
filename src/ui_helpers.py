"""
UI helper functions for the Streamlit app.
"""
import pandas as pd
import streamlit as st
import time


def clean_age_data(df):
    """Clean age data by removing semicolon-separated values (bot responses)."""
    if 'Age range' in df.columns:
        # Remove rows with semicolon-separated values
        df = df[~df['Age range'].astype(str).str.contains(';', na=False)]
        # Convert to numeric, dropping any non-numeric values
        df['Age range'] = pd.to_numeric(df['Age range'], errors='coerce')
        # Drop rows where age is NaN
        df = df.dropna(subset=['Age range'])
    return df


def group_summary(group):
    """Generate a summary string for a group."""
    if not group["conditions"]:
        return "(no conditions)"
    parts = []
    for cond in group["conditions"]:
        col = cond.get("column")
        vals = cond.get("values", [])
        if not col or not vals:
            continue
        joiner = f" {cond.get('combine', 'OR')} "
        val_str = joiner.join(str(v) for v in vals)
        parts.append(f"{col}: {val_str}")
    logic = group.get("logic", "AND")
    return f" {logic} ".join(parts) if parts else "(no conditions)"


def audience_summary(aud, auto_group_name_func):
    """Generate a summary string for an audience."""
    if not aud["groups"]:
        return "(no groups)"
    group_names = [g.get("name") or auto_group_name_func(g) for g in aud["groups"] if g.get("name") or auto_group_name_func(g)]
    if not group_names:
        return "(no groups)"
    joiner = f" {aud.get('top_logic', 'AND')} "
    return joiner.join(group_names)


def auto_group_name(group_idx):
    """Generate a default name for a group."""
    return f"Attribute Group {group_idx + 1}"


def calculate_sample_sizes(df, cond, delay=0.5):
    """Calculate sample sizes with a delay to prevent UI issues."""
    if df is not None and cond.get("column") and cond.get("values"):
        time.sleep(delay)  # Add a small delay
        col = cond["column"]
        vals = cond["values"]
        count = df[df[col].isin(vals)].shape[0]
        return count
    return None


def calculate_audience_sample_size(df, aud):
    """
    Calculate sample size for an audience based on its groups and conditions.
    
    Args:
        df: DataFrame with the data
        aud: Audience dictionary with groups and conditions
    
    Returns:
        Integer sample size
    """
    if df is None or not aud.get("groups"):
        return 0
    
    group_masks = []
    for group in aud["groups"]:
        masks = []
        for cond in group["conditions"]:
            col = cond.get("column")
            vals = cond.get("values", [])
            if col and vals:
                # Handle boolean columns specially (like _customer columns)
                if df[col].dtype == bool or col.endswith('_customer'):
                    # Convert string values to boolean for comparison
                    bool_values = [v if isinstance(v, bool) else v.lower() == 'true' for v in vals]
                    masks.append(df[col].isin(bool_values))
                # Handle numeric columns specially (like Age range)
                elif pd.api.types.is_numeric_dtype(df[col].dtype):
                    # Convert string values to numbers for comparison
                    try:
                        numeric_values = [int(v) if isinstance(v, str) else v for v in vals]
                        masks.append(df[col].isin(numeric_values))
                    except (ValueError, TypeError):
                        # Fall back to original values if conversion fails
                        masks.append(df[col].isin(vals))
                else:
                    masks.append(df[col].isin(vals))
        if masks:
            if group.get("logic", "OR") == "AND":
                group_mask = masks[0]
                for m in masks[1:]:
                    group_mask &= m
            else:
                group_mask = masks[0]
                for m in masks[1:]:
                    group_mask |= m
            group_masks.append(group_mask)
    
    if group_masks:
        if aud.get("top_logic", "OR") == "AND":
            total_mask = group_masks[0]
            for m in group_masks[1:]:
                total_mask &= m
        else:
            total_mask = group_masks[0]
            for m in group_masks[1:]:
                total_mask |= m
        return total_mask.sum()
    
    return 0
