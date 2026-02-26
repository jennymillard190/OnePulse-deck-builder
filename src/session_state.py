"""
Session state management for Streamlit app.
Centralizes initialization and cleanup logic.
"""
import streamlit as st


def initialize_session_state():
    """Initialize all session state variables."""
    defaults = {
        "audiences": [],
        "editing_audience": None,
        "new_audience": None,
        "processed_data": None,
        "pptx_bytes": None,
        "df": None,
        "audience_groups": [],
        "calculating_sample": False,
        "analysis_mode": "Text Categorisation",
        "selected_text_column": None,
        "category_labels": [],
        "categorized_df": None,
        "text_token_count": None,
        "non_null_responses": None,
        "breakdown_column": None,
        "previous_analysis_mode": None,
        "token_count_cache": {},
        "gemini_api_key": None,
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def clear_mode_state(target_mode: str):
    """
    Clear session state when switching between modes.
    
    Args:
        target_mode: The mode being switched to ("OnePulse Powerpoint Charting" or "Text Categorisation")
    """
    previous_mode = st.session_state.get("previous_analysis_mode")
    
    if previous_mode is not None and previous_mode != target_mode:
        if target_mode == "OnePulse Powerpoint Charting":
            # Switching to OnePulse mode - clear Text Categorisation state
            st.session_state.categorized_df = None
            st.session_state.text_token_count = None
            st.session_state.non_null_responses = None
            st.session_state.selected_text_column = None
            st.session_state.category_labels = []
            st.session_state.breakdown_column = None
            st.session_state.token_count_cache = {}
        elif target_mode == "Text Categorisation":
            # Switching to Text Categorisation mode - clear OnePulse state
            st.session_state.audiences = []
            st.session_state.audience_groups = []
            st.session_state.processed_data = None
            st.session_state.pptx_bytes = None
            if "file_generated" in st.session_state:
                st.session_state.file_generated = False
            if "generated_file_path" in st.session_state:
                del st.session_state.generated_file_path
            if "generated_file_name" in st.session_state:
                del st.session_state.generated_file_name
    
    st.session_state.previous_analysis_mode = target_mode
    st.session_state.analysis_mode = target_mode
