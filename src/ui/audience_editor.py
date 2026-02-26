"""
Audience editor UI component for creating and editing audience definitions.
"""
import streamlit as st
from src.ui_helpers import auto_group_name
from src.audience_utils import save_audience_definitions
from src.template_matcher import get_column_values


def get_available_columns(df):
    """
    Get available columns, prioritizing bank customer columns.
    
    Args:
        df: DataFrame or None
    
    Returns:
        List of column names, with _customer columns first
    """
    if df is None:
        return []
    
    available_columns = df.columns.tolist()
    bank_customer_cols = [col for col in available_columns if col.endswith('_customer')]
    other_cols = [col for col in available_columns if not col.endswith('_customer')]
    return bank_customer_cols + other_cols


def audience_editor(aud, idx, session_state):
    """
    Render the audience editor UI.
    
    Args:
        aud: Audience dictionary to edit
        idx: Index of the audience ("new" for new audience, or integer for existing)
        session_state: Streamlit session state object
    """
    df = session_state.get('df')
    columns = get_available_columns(df)

    with st.container():
        # Initial state - just name input
        if not aud.get("name"):
            with st.form(key=f"audience_name_form_{idx}", clear_on_submit=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_name = st.text_input("Audience Name", key=f"new_name_{idx}")
                with col2:
                    save_clicked = st.form_submit_button("Save Name")
                if save_clicked and new_name:
                    aud["name"] = new_name
                    st.rerun()
            return

        # After naming - show header and first group
        st.subheader(aud["name"])
        
        # Only show top-level logic if there's more than one group
        if len(aud["groups"]) > 1:
            aud["top_logic"] = st.radio("Combine Groups With", ["AND", "OR"], horizontal=True, key=f"top_logic_{idx}")
        
        # First group is always present
        if not aud["groups"]:
            aud["groups"].append({"conditions": [], "logic": "OR", "name": auto_group_name(0)})
        
        # Show groups
        for g_idx, group in enumerate(aud["groups"]):
            with st.expander(group.get("name", auto_group_name(g_idx)), expanded=True):
                # Group name
                col1, col2 = st.columns([3, 1])
                with col1:
                    group["name"] = st.text_input("Group Name", value=group.get("name", auto_group_name(g_idx)), key=f"group_name_{idx}_{g_idx}")
                # Only show group logic if there's more than one condition
                if len(group["conditions"]) > 1:
                    group["logic"] = st.radio("Combine Values With", ["AND", "OR"], horizontal=True, key=f"group_logic_{idx}_{g_idx}")
                # Show conditions
                for c_idx, cond in enumerate(group["conditions"]):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        current_col = cond.get("column")
                        col_index = columns.index(current_col) if current_col in columns else 0
                        cond["column"] = st.selectbox("Column", columns, index=col_index, key=f"col_{idx}_{g_idx}_{c_idx}")
                    with col2:
                        values = get_column_values(cond["column"], df)
                        if set(values) == {"True", "False"}:
                            cond["values"] = ["True"]
                        else:
                            cond["values"] = []
                        # Get the current values and ensure they exist in the new values list
                        current_values = cond.get("values", [])
                        valid_values = [v for v in current_values if v in values]
                        cond["values"] = st.multiselect("Values", values, default=valid_values, key=f"vals_{idx}_{g_idx}_{c_idx}")
                    with col3:
                        if st.button("🗑️", key=f"del_cond_{idx}_{g_idx}_{c_idx}"):
                            group["conditions"].pop(c_idx)
                            st.rerun()
                
                # Add condition button
                if st.button("Add Attribute", key=f"add_cond_{idx}_{g_idx}"):
                    group["conditions"].append({"column": columns[0] if columns else None, "values": []})
                    st.rerun()
                if len(aud["groups"]) > 1:
                    if st.button("Delete Group", key=f"del_group_{idx}_{g_idx}"):
                        aud["groups"].pop(g_idx)
                        st.rerun()
        
        # Add group button
        if st.button("Add Group", key=f"add_group_{idx}"):
            # Get available columns from the uploaded DataFrame
            df = session_state.get('df')
            columns = get_available_columns(df)
            # Create a new group with default name and one empty condition if columns exist
            new_group_idx = len(aud["groups"])
            new_group = {
                "name": auto_group_name(new_group_idx),
                "conditions": [],
                "logic": "OR"
            }
            if columns:
                new_group["conditions"].append({"column": columns[0], "values": []})
            aud["groups"].append(new_group)
            st.rerun()
        
        # Save/Cancel buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Save Audience", key=f"save_aud_{idx}"):
                if idx == "new":
                    session_state.audiences.append(aud)
                else:
                    session_state.audiences[idx] = aud
                session_state.editing_audience = None
                session_state.new_audience = None
                save_audience_definitions(session_state.audiences)  # Save to JSON file
                st.rerun()
        with col2:
            if st.button("Cancel", key=f"cancel_aud_{idx}"):
                session_state.editing_audience = None
                session_state.new_audience = None
                st.rerun()
