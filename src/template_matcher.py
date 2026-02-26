"""
Template matching logic for pre-built audience templates.
"""
import os
import json
import pandas as pd
import streamlit as st


def get_column_values(col, df):
    """
    Get unique values from a column in the DataFrame.
    
    Args:
        col: Column name
        df: DataFrame
    
    Returns:
        List of unique values
    """
    if df is None or col is None or col not in df.columns:
        return []
    
    vals = set()
    for cell in df[col]:
        if isinstance(cell, list):
            vals.update(cell)
        else:
            vals.add(cell)
    vals = [str(v) for v in vals if v != '' and v is not None]
    return sorted(vals)


def load_prebuilt_templates():
    """Load pre-built templates from JSON file."""
    try:
        template_path = os.path.join("src", "prebuilt_templates.json")
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return json.load(f)
        else:
            st.warning("Pre-built templates file not found. Creating default templates.")
            return {"templates": {}}
    except Exception as e:
        st.error(f"Error loading pre-built templates: {e}")
        return {"templates": {}}


def find_matching_column(column_patterns, available_columns):
    """Find a column that matches any of the patterns."""
    for pattern in column_patterns:
        # Skip None, NaN, or non-string patterns
        if pattern is None or pd.isna(pattern) or not isinstance(pattern, str):
            continue
        for col in available_columns:
            if isinstance(col, str) and pattern.lower() in col.lower():
                return col
    return None


def find_matching_values(target_values, value_mappings, actual_values):
    """Find values that match the target values using mappings."""
    if not value_mappings:
        # No mappings, just use exact matches
        return [val for val in target_values if val is not None and not pd.isna(val) and val in actual_values]
    
    matched_values = []
    for target in target_values:
        # Skip None or NaN values
        if target is None or pd.isna(target):
            continue
        if target in actual_values:
            matched_values.append(target)
        elif target in value_mappings:
            # Check mapped values
            for mapped_val in value_mappings[target]:
                if mapped_val in actual_values:
                    matched_values.append(mapped_val)
                    break
    return matched_values


def get_applicable_templates(df):
    """Get templates that are applicable to the current data."""
    templates = load_prebuilt_templates()
    applicable = {}
    
    if df is None:
        return applicable
    
    available_columns = df.columns.tolist()
    
    for template_name, template in templates.get("templates", {}).items():
        column_patterns = template.get("column_patterns", [])
        # Ensure column_patterns is a list
        if not isinstance(column_patterns, list):
            column_patterns = []
        
        # --- Age group logic: always use 'Age range' if present ---
        if "age" in template_name.lower():
            if "Age range" in available_columns:
                matching_column = "Age range"
            else:
                matching_column = find_matching_column(column_patterns, available_columns)
                if not matching_column:
                    st.warning("No 'Age range' column found. Age-based templates require a column with individual ages.")
                    continue
        else:
            matching_column = find_matching_column(column_patterns, available_columns)
        
        if matching_column:
            actual_values = get_column_values(matching_column, df)
            # For age templates, we need to check if we have numeric ages
            if "age" in template_name.lower():
                numeric_ages = [v for v in actual_values if v.isdigit()]
                if len(numeric_ages) >= 3:  # Need at least a few age values
                    applicable[template_name] = {
                        "template": template,
                        "matching_column": matching_column,
                        "confidence": "high" if len(numeric_ages) > 10 else "medium"
                    }
            else:
                # For other templates, check if we have matching values
                value_mappings = template.get("value_mappings", {})
                has_valid_values = False
                for audience in template.get("audiences", []):
                    for group in audience.get("groups", []):
                        for condition in group.get("conditions", []):
                            target_values = condition.get("values", [])
                            matched_values = find_matching_values(target_values, value_mappings, actual_values)
                            if matched_values:
                                has_valid_values = True
                                break
                        if has_valid_values:
                            break
                    if has_valid_values:
                        break
                if has_valid_values:
                    applicable[template_name] = {
                        "template": template,
                        "matching_column": matching_column,
                        "confidence": "high"
                    }
    return applicable


def add_prebuilt_template(template_name, applicable_templates, session_state):
    """
    Add a pre-built template to the current audiences and groups.
    
    Args:
        template_name: Name of the template to add
        applicable_templates: Dict of applicable templates
        session_state: Streamlit session state object
    """
    if template_name not in applicable_templates:
        st.error(f"Template '{template_name}' is not applicable to your data.")
        return
    
    template_info = applicable_templates[template_name]
    template = template_info["template"]
    matching_column = template_info["matching_column"]
    
    # Get actual values from the data
    df = session_state.get('df')
    actual_values = get_column_values(matching_column, df)
    
    # Get the column data type for type conversion
    column_dtype = df[matching_column].dtype if df is not None else None
    
    # Adapt audiences based on actual data
    adapted_audiences = []
    for audience in template.get("audiences", []):
        adapted_audience = audience.copy()
        
        for group in adapted_audience["groups"]:
            for condition in group["conditions"]:
                # Update column name to match actual data
                condition["column"] = matching_column
                
                # Find matching values
                value_mappings = template.get("value_mappings", {})
                target_values = condition.get("values", [])
                matched_values = find_matching_values(target_values, value_mappings, actual_values)
                
                if matched_values:
                    # Convert values to match column data type
                    if column_dtype and pd.api.types.is_numeric_dtype(column_dtype):
                        # For numeric columns, convert string values to numbers
                        try:
                            condition["values"] = [int(v) for v in matched_values if v.isdigit()]
                        except (ValueError, TypeError):
                            condition["values"] = matched_values
                    else:
                        condition["values"] = matched_values
                else:
                    # If no matches found, skip this audience
                    st.warning(f"No matching values found for {audience['name']}. Skipping.")
                    continue
        
        adapted_audiences.append(adapted_audience)
    
    if not adapted_audiences:
        st.error(f"No valid audiences could be created from the '{template_name}' template.")
        return
    
    # Add adapted audiences
    for audience in adapted_audiences:
        # Check if audience name already exists
        existing_names = [aud["name"] for aud in session_state.audiences]
        if audience["name"] not in existing_names:
            session_state.audiences.append(audience)
    
    # Add group
    audience_names = [aud["name"] for aud in adapted_audiences]
    existing_group_names = [group["name"] for group in session_state.audience_groups]
    
    group_name = template.get("group_name", template_name)
    
    # Check if group already exists
    if group_name not in existing_group_names:
        session_state.audience_groups.append({
            "name": group_name,
            "audiences": audience_names
        })
    else:
        # Add audiences to existing group
        for group in session_state.audience_groups:
            if group["name"] == group_name:
                for name in audience_names:
                    if name not in group["audiences"]:
                        group["audiences"].append(name)
                break
    
    st.success(f"Added {len(adapted_audiences)} audiences from '{template_name}' template!")
    st.rerun()
