import streamlit as st
import pandas as pd
import json
import os
import shutil
import copy
import hashlib
from src import config, process_data, generate_presentation
from src.data_loader import load_uploaded_file
from src.text_categoriser import get_text_columns, preview_column_data, categorise_responses, get_categorisation_summary, get_categorisation_summary_with_breakdown, load_flexible_data, count_tokens_for_column, estimate_categorisation_cost
from src.session_state import initialize_session_state, clear_mode_state
from src.chart_helpers import create_grouped_bar_chart, create_category_distribution_chart, create_stacked_breakdown_chart
from src.audience_utils import convert_audiences_to_json, save_audience_definitions
from src.template_matcher import get_applicable_templates, add_prebuilt_template, get_column_values
from src.ui_helpers import clean_age_data, group_summary, audience_summary, auto_group_name, calculate_audience_sample_size
from src.ui.audience_editor import audience_editor
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Suppress debug logs from all modules
for module in ['src.data_loader', 'src.data_processor', 'src.ppt_generator']:
    logging.getLogger(module).setLevel(logging.WARNING)

# Only show INFO level messages from ppt_generator
logging.getLogger('src.ppt_generator').setLevel(logging.INFO)

# --- Initialize session state ---
initialize_session_state()

# --- Page config ---
st.set_page_config(
    page_title="Survey Response Analyser",
    page_icon="🎯",
    layout="wide"
)

st.title("Survey Response Analyser")

# --- Session state for audiences and UI ---
if "open_audience" not in st.session_state:
    st.session_state.open_audience = None  # Index of the audience being edited
if "open_group" not in st.session_state:
    st.session_state.open_group = None  # (audience_idx, group_idx)

# --- Analysis Mode Selection (before file upload) ---
st.subheader("Select Analysis Mode")
analysis_mode = st.radio(
    "Choose the type of analysis you want to perform:",
    options=["Text Categorisation", "OnePulse Powerpoint Charting"],
    index=0 if st.session_state.analysis_mode == "Text Categorisation" else 1,
    horizontal=True,
    help="Text Categorisation: Categorise open-ended text responses into predefined categories. OnePulse Powerpoint Charting: Create audience segments and generate PowerPoint presentations (requires OnePulse export format)."
)

# Clean up session state when switching modes
clear_mode_state(analysis_mode)

# --- File uploader ---
uploaded = st.file_uploader(
    """
    Upload Data File (CSV, JSON, XLSX), containing survey responses.
    The file should have one row per response.
    """,
    type=["csv", "json", "xlsx", "xls"]
)

df = None
if uploaded:
    # Check if this is a new file (different from previously loaded)
    previous_filename = st.session_state.get('input_filename')
    is_new_file = previous_filename is None or previous_filename != uploaded.name
    
    try:
        # Use different data loaders based on analysis mode
        if st.session_state.analysis_mode == "OnePulse Powerpoint Charting":
            df = load_uploaded_file(uploaded)
            # Clean age data to remove bot responses
            df = clean_age_data(df)
        else:  # Text Categorisation mode
            df = load_flexible_data(uploaded)
        
        # Clear categorization results if this is a new file
        if is_new_file and st.session_state.analysis_mode == "Text Categorisation":
            st.session_state.categorized_df = None
            st.session_state.text_token_count = None
            st.session_state.non_null_responses = None
            # Clear selected column if it doesn't exist in new dataframe
            if st.session_state.selected_text_column is not None:
                if st.session_state.selected_text_column not in df.columns:
                    st.session_state.selected_text_column = None
            st.session_state.category_labels = []
            st.session_state.breakdown_column = None
            # Clear token count cache
            st.session_state.token_count_cache = {}
        
        st.session_state.df = df
        # Store the original filename for PPT generation
        st.session_state.input_filename = uploaded.name
        # Show number of rows loaded
        st.success(f"Loaded {len(df)} responses from {uploaded.name}")
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

# --- Divider after file upload ---
if st.session_state.get('df') is not None:
    st.divider()


# --- OnePulse Powerpoint Charting Mode ---
if st.session_state.get('df') is not None and st.session_state.analysis_mode == "OnePulse Powerpoint Charting":
    # --- Pre-built templates section (only show after file upload) ---
    applicable_templates = get_applicable_templates(st.session_state.df)
    
    if applicable_templates:
        st.subheader("🎯 Quick Start: Pre-built Audience Templates")
        st.write("Add commonly used audience segments to speed up your analysis.")
        
        # Create columns for template buttons
        template_cols = st.columns(len(applicable_templates))
        
        for i, (template_name, template_info) in enumerate(applicable_templates.items()):
            with template_cols[i]:
                template = template_info["template"]
                confidence = template_info["confidence"]
                
                # Color code based on confidence
                if confidence == "high":
                    button_color = "primary"
                else:
                    button_color = "secondary"
                
                if st.button(f"Add {template_name}", key=f"template_{template_name}", type=button_color):
                    add_prebuilt_template(template_name, applicable_templates, st.session_state)
                
                st.caption(template["description"])
                if confidence == "medium":
                    st.caption("⚠️ Limited data available")
        
        st.divider()


# --- Audience Editor ---

# --- List existing audiences ---
if st.session_state.audiences:
    st.subheader("Existing Audiences")
    for i, aud in enumerate(st.session_state.audiences):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            # Calculate and display sample size for this audience
            sample_size = calculate_audience_sample_size(st.session_state.get('df'), aud)
            
            st.write(f"{aud['name']}: {audience_summary(aud, auto_group_name)} (Sample size: {sample_size})")
        with col2:
            if st.button("Edit", key=f"edit_{i}"):
                st.session_state.editing_audience = i
                st.rerun()
        with col3:
            if st.button("Delete", key=f"delete_{i}"):
                # Remove this audience from any groups it's in
                for group in st.session_state.audience_groups:
                    if aud["name"] in group["audiences"]:
                        group["audiences"].remove(aud["name"])
                st.session_state.audiences.pop(i)
                st.rerun()

    # --- Audience Groups ---
    st.subheader("Audience Groups")
    st.write("Group your audiences together to compare them in the presentation.")
    
    # Add new group button
    if st.button("Add Group"):
        st.session_state.audience_groups.append({
            "name": f"Group {len(st.session_state.audience_groups) + 1}",
            "audiences": []
        })
        st.rerun()
    
    # List existing groups
    for i, group in enumerate(st.session_state.audience_groups):
        with st.expander(group["name"], expanded=True):
            # Group name
            group["name"] = st.text_input("Group Name", value=group["name"], key=f"group_name_{i}")
            
            # Available audiences (excluding those already in other groups)
            available_audiences = []
            for aud in st.session_state.audiences:
                is_available = True
                for other_group in st.session_state.audience_groups:
                    if other_group != group and aud["name"] in other_group["audiences"]:
                        is_available = False
                        break
                if is_available:
                    available_audiences.append(aud["name"])
            
            # Multi-select for audiences
            group["audiences"] = st.multiselect(
                "Select Audiences",
                options=available_audiences + group["audiences"],  # Include current selections
                default=group["audiences"],
                key=f"group_audiences_{i}"
            )
            
            # Delete group button
            if st.button("Delete Group", key=f"delete_group_{i}"):
                st.session_state.audience_groups.pop(i)
                st.rerun()

# --- Open audience editor if needed ---
if st.session_state.editing_audience is not None:
    if st.session_state.editing_audience == "new":
        audience_editor(st.session_state.new_audience, idx="new", session_state=st.session_state)
    else:
        audience_editor(st.session_state.audiences[st.session_state.editing_audience], idx=st.session_state.editing_audience, session_state=st.session_state)

# --- Add new audience button (only in OnePulse mode) ---
if st.session_state.get('df') is not None and st.session_state.analysis_mode == "OnePulse Powerpoint Charting":
    if st.session_state.editing_audience is None:  # Only show when not editing
        if st.button("Add Audience"):
            st.session_state.editing_audience = "new"
            # Get available columns from the uploaded DataFrame
            df = st.session_state.get('df')
            if df is not None:
                available_columns = df.columns.tolist()
                bank_customer_cols = [col for col in available_columns if col.endswith('_customer')]
                other_cols = [col for col in available_columns if not col.endswith('_customer')]
                columns = bank_customer_cols + other_cols
            else:
                columns = []
            # Initialize first group with one empty condition if columns exist
            first_group = {"name": auto_group_name(0), "conditions": [], "logic": "OR"}
            if columns:
                first_group["conditions"].append({"column": columns[0], "values": []})
            st.session_state.new_audience = {"name": "", "groups": [first_group]}
            st.rerun()

# --- Export type selection and Generate (only when audiences exist) ---
if st.session_state.audiences and st.session_state.analysis_mode == "OnePulse Powerpoint Charting":
    # --- Export type selection ---
    export_type = st.radio(
        "Select PowerPoint Export Type:",
        options=["Full", "Condensed"],
        index=1,  # Ensure 'Condensed' is the default
        horizontal=True,
        help="Full: All slides (totals, all segments, groups, and individual segments). Condensed: Only group slides and ungrouped audience segments, with no duplication."
    )
    export_type_key = export_type.lower()

    # --- Generate JSON and run main.py ---
    if st.session_state.get('df') is not None:
        # Use form to allow download after generate
        with st.form(key="generate_form"):
            generate_clicked = st.form_submit_button("Generate")
            if generate_clicked:
                # Set flag to indicate file generation is in progress
                st.session_state.file_generated = False
                st.session_state.generated_file_path = None
                st.session_state.generated_file_name = None
                # Convert audiences to JSON format
                audience_defs = convert_audiences_to_json(st.session_state.audiences)

                # Add audience groups to the JSON
                audience_defs["__groups__"] = [
                    {
                        "name": group["name"],
                        "audiences": group["audiences"]
                    }
                    for group in st.session_state.audience_groups
                ]

                json_str = json.dumps(audience_defs, indent=2)
                st.code(json_str, language="json")

                # save to src/audience_segments.JSON
                project_root = os.getcwd()
                output_path = os.path.join(project_root, "src", "audience_segments.json")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(json_str)
                st.success(f"Saved JSON to {output_path}")

                # Process the data and generate the presentation
                if 'df' in st.session_state:
                    try:
                        # Process the data - PASS THE AUDIENCE DEFINITIONS!
                        # Make a copy for process_data (which will mutate it by removing __groups__)
                        audience_defs_copy = copy.deepcopy(audience_defs)
                        raw_audience_data, combined_data, group_audience_names = process_data(st.session_state.df, audience_defs=audience_defs_copy)
                        
                        # Store the processed data in session state
                        st.session_state.processed_data = (raw_audience_data, combined_data)
                        
                        # Display the processed data
                        st.subheader("Processed Data")
                        
                        # Display raw data summary
                        st.write("### Raw Data Summary")
                        st.write(f"Total respondents: {len(st.session_state.df)}")
                        st.write("Sample of raw data:")
                        st.dataframe(st.session_state.df.head())
                        
                        # Display processed questions
                        st.write("### Processed Questions")
                        for title, categories, segments in raw_audience_data:
                            st.write(f"#### {title}")
                            # Create a DataFrame for better display
                            data = {
                                'Category': categories,
                                'Total': segments[0][1]  # First segment is always Total
                            }
                            # Add audience segments
                            for audience_name, values, _ in segments[1:]:
                                data[audience_name] = values
                            
                            df_display = pd.DataFrame(data)
                            st.dataframe(df_display)
                            
                            # Add a bar chart using Plotly
                            create_grouped_bar_chart(df_display, title, "raw_audience_chart")
                        
                        # Display combined data
                        st.write("### Combined Data")
                        for title, categories, segments in combined_data:
                            st.write(f"#### {title}")
                            # Create a DataFrame for better display
                            data = {
                                'Category': categories,
                                'Total': segments[0][1]  # First segment is always Total
                            }
                            # Add audience segments
                            for audience_name, values, _ in segments[1:]:
                                data[audience_name] = values
                            
                            df_display = pd.DataFrame(data)
                            st.dataframe(df_display)
                            
                            # Add a bar chart using Plotly
                            create_grouped_bar_chart(df_display, title, "combined_data_chart")
                        
                        # Generate the presentation
                        output_path = os.path.join(project_root, config.get_output_pptx_path(st.session_state.input_filename, export_type_key))
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        generate_presentation(raw_audience_data, combined_data, output_path, export_type=export_type_key, audience_defs=audience_defs)
                        st.success(f"Generated presentation at {output_path}")
                        
                        # Store file info in session state for download button outside form
                        with open(output_path, "rb") as f:
                            st.session_state.pptx_bytes = f.read()
                        st.session_state.file_generated = True
                        st.session_state.generated_file_path = output_path
                        st.session_state.generated_file_name = os.path.basename(output_path)
                        
                    except Exception as e:
                        st.error(f"Error processing data: {str(e)}")
                        raise e
                else:
                    st.error("No data file has been uploaded yet.")

    # --- Download button (outside form) ---
    if st.session_state.get('file_generated', False) and st.session_state.get('pptx_bytes') is not None:
        st.download_button(
            label="Download Presentation",
            data=st.session_state.pptx_bytes,
            file_name=st.session_state.generated_file_name,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

# --- Helper function to get Gemini API key ---
def get_gemini_api_key():
    """
    Get Gemini API key from environment variable or session state.
    Checks environment variable first, then falls back to session state.
    
    Returns:
        API key string if available, None otherwise
    """
    # Check environment variable first
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key
    
    # Fall back to session state
    return st.session_state.get("gemini_api_key")

# --- Text Categorisation Mode ---
if st.session_state.get('df') is not None and st.session_state.analysis_mode == "Text Categorisation":
    st.subheader("📝 Text Categorisation")
    st.write("Categorise open-ended text responses into predefined categories.")
    
    # API Key input (only show if not set in environment variable)
    if not os.getenv("GEMINI_API_KEY"):
        st.subheader("🔑 API Key Configuration")
        st.write("Enter your Gemini API key to enable text categorisation. The key will be stored in your session (not saved to disk).")
        
        api_key_input = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("gemini_api_key", ""),
            type="password",
            help="Enter your Google Gemini API key. You can get one from https://aistudio.google.com/app/apikey"
        )
        
        if api_key_input:
            st.session_state.gemini_api_key = api_key_input
            st.success("API key saved for this session.")
        elif st.session_state.get("gemini_api_key"):
            # Key already set, show that it's configured
            st.info("✅ API key is configured for this session.")
        else:
            st.warning("⚠️ API key is required for text categorisation. Please enter your key above.")
        
        st.divider()
    
    df = st.session_state.df
    
    # Get suitable text columns
    text_columns = get_text_columns(df)
    
    if not text_columns:
        st.warning("No suitable text columns found in your data. Please ensure your data contains open-ended text responses.")
        st.info("Suitable columns should contain text responses (not structured data like multiple choice questions).")
    else:
        # Column selection
        st.subheader("1. Select Text Column")
        selected_column = st.selectbox(
            "Choose the column containing text responses to categorize:",
            options=text_columns,
            index=0 if st.session_state.selected_text_column is None else text_columns.index(st.session_state.selected_text_column) if st.session_state.selected_text_column in text_columns else 0,
            help="Select the column that contains the open-ended text responses you want to categorize."
        )
        st.session_state.selected_text_column = selected_column
        
        # Show preview of selected column
        if selected_column:
            preview_data = preview_column_data(df, selected_column)
            st.session_state.non_null_responses = preview_data["non_null_responses"]  # Store for cost calculation
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Responses", preview_data["total_responses"])
            with col2:
                st.metric("Non-null Responses", preview_data["non_null_responses"])
            
            st.write(f"**Average response length:** {preview_data['average_length']} characters")
            
            # Show sample responses
            st.write("**Sample responses:**")
            for i, response in enumerate(preview_data["sample_responses"], 1):
                st.write(f"{i}. {response}")
            
            # Token count with caching
            api_key = get_gemini_api_key()
            if api_key:
                # Create hash of column data for caching
                column_data_str = df[selected_column].dropna().astype(str).tolist()
                column_data_hash = hashlib.md5(str(sorted(column_data_str)).encode()).hexdigest()
                
                # Check cache
                cache_key = f"{selected_column}_{column_data_hash}"
                token_count = None
                
                if cache_key in st.session_state.token_count_cache:
                    token_count = st.session_state.token_count_cache[cache_key]
                    st.session_state.text_token_count = token_count
                    token_count_millions = token_count / 1_000_000
                    st.metric("Estimated Token Count", f"{token_count_millions:.2f}M", help="Total tokens for all text responses in the selected column.\nThis is an estimate before categorisation, and does not include the system prompt or output tokens.\n(Cached)")
                else:
                    # Not in cache, calculate and store
                    with st.spinner("Counting tokens..."):
                        token_count = count_tokens_for_column(df, selected_column, api_key=api_key)
                        if token_count is not None:
                            st.session_state.token_count_cache[cache_key] = token_count
                            token_count_millions = token_count / 1_000_000
                            st.session_state.text_token_count = token_count  # Store for cost calculation
                            st.metric("Estimated Token Count", f"{token_count_millions:.2f}M", help="Total tokens for all text responses in the selected column.\nThis is an estimate before categorisation, and does not include the system prompt or output tokens.")
                        else:
                            st.session_state.text_token_count = None
                            st.info("Unable to count tokens. Please check your API key.")
            else:
                st.session_state.text_token_count = None
                st.info("API key not set. Token count unavailable. Please enter your Gemini API key above.")
        
        st.divider()
        
        # Category input
        st.subheader("2. Define Categories")
        st.write("Enter the category labels you want to use for categorisation:")
        
        # Category input method
        category_input_method = st.radio(
            "How would you like to enter categories?",
            options=["One per line", "Comma separated"],
            horizontal=True
        )
        
        if category_input_method == "One per line":
            category_text = st.text_area(
                "Enter categories (one per line):",
                value="\n".join(st.session_state.category_labels),
                height=150,
                help="Enter each category on a separate line. For example:\n\nPositive\nNegative\nNeutral"
            )
            categories = [cat.strip() for cat in category_text.split('\n') if cat.strip()]
        else:
            category_text = st.text_input(
                "Enter categories (comma separated):",
                value=", ".join(st.session_state.category_labels),
                help="Enter categories separated by commas. For example: Positive, Negative, Neutral"
            )
            categories = [cat.strip() for cat in category_text.split(',') if cat.strip()]
        
        st.session_state.category_labels = categories
        
        # Show categories
        if categories:
            st.write("**Defined categories:**")
            for i, cat in enumerate(categories, 1):
                st.write(f"{i}. {cat}")
            
            # Price estimate
            api_key = get_gemini_api_key()
            if selected_column and st.session_state.get('text_token_count') is not None and st.session_state.get('non_null_responses') is not None:
                if api_key:
                    with st.spinner("Calculating cost estimate..."):
                        cost_estimate = estimate_categorisation_cost(
                            text_token_count=st.session_state.text_token_count,
                            num_responses=st.session_state.non_null_responses,
                            categories=categories,
                            api_key=api_key
                        )
                        
                        if cost_estimate['total_cost'] > 0:
                            st.write("**Estimated Cost:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Input Cost", f"${cost_estimate['input_cost']:.2f}", 
                                         help=f"Based on {cost_estimate['input_tokens']/1_000_000:.2f}M input tokens @ $0.075 per 1M tokens")
                            with col2:
                                st.metric("Output Cost", f"${cost_estimate['output_cost']:.2f}",
                                         help=f"Based on {cost_estimate['output_tokens']/1_000_000:.2f}M output tokens @ $0.30 per 1M tokens")
                            with col3:
                                st.metric("Total Cost", f"${cost_estimate['total_cost']:.2f}",
                                         help="Total estimated cost for categorising all responses")
                        else:
                            st.info("Unable to calculate cost estimate.")
                else:
                    st.info("API key not set. Cost estimate unavailable. Please enter your Gemini API key above.")
        
        st.divider()
        
        # Processing section
        st.subheader("3. Categorisation Processing")
        
        if selected_column and categories:
            # Show what the output will look like
            st.write("**Preview of categorisation results:**")
            st.write(f"New columns that will be created:")
            for category in categories:
                safe_category = category.lower().replace(' ', '_').replace('-', '_')
                safe_category = re.sub(r'[^a-z0-9_]', '', safe_category)
                new_column_name = f"{selected_column}_{safe_category}"
                st.write(f"- `{new_column_name}` (True/False)")
            
            # Processing button
            api_key = get_gemini_api_key()
            if st.button("Process Categorisation"):
                if not api_key:
                    st.error("API key not set. Please enter your Gemini API key above before processing.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(progress):
                        progress_bar.progress(progress)
                        status_text.text(f"Processing: {int(progress * 100)}% complete")
                    
                    try:
                        status_text.text("Starting categorisation...")
                        result_df = categorise_responses(
                            df,
                            selected_column,
                            categories,
                            max_workers=10,
                            progress_callback=update_progress,
                            api_key=api_key
                        )
                        st.session_state.categorized_df = result_df
                        st.session_state.df = result_df  # Update main dataframe
                        status_text.text("Categorisation complete!")
                        st.success(f"Successfully categorised {len(result_df)} responses!")
                        st.rerun()
                    except Exception as e:
                        status_text.text("Error during categorisation")
                        st.error(f"Error during categorisation: {str(e)}")
                        import traceback
                        st.error(traceback.format_exc())
            
            # Show results if categorisation has been completed
            if st.session_state.get('categorized_df') is not None and selected_column and categories:
                st.divider()
                st.subheader("4. Categorisation Results")
                
                result_df = st.session_state.categorized_df
                
                # Breakdown column selector
                all_columns = result_df.columns.tolist()
                breakdown_options = ["None"] + all_columns
                breakdown_index = 0
                if "breakdown_column" in st.session_state and st.session_state.breakdown_column in breakdown_options:
                    breakdown_index = breakdown_options.index(st.session_state.breakdown_column)
                
                selected_breakdown = st.selectbox(
                    "Break down by (optional):",
                    options=breakdown_options,
                    index=breakdown_index,
                    help="Select a column to see category breakdown by its values. For example, select 'Gender' to see how each category varies by gender."
                )
                
                if selected_breakdown == "None":
                    st.session_state.breakdown_column = None
                    # Get summary statistics without breakdown
                    summary = get_categorisation_summary(result_df, selected_column, categories)
                    
                    # Display summary statistics
                    st.write("**Summary Statistics:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Responses", summary["total_responses"])
                    with col2:
                        st.metric("Categories", len(categories))
                    
                    # Create summary table
                    summary_data = []
                    for category, stats in summary["categories"].items():
                        summary_data.append({
                            "Category": category,
                            "Count": stats["count"],
                            "Percentage": f"{stats['percentage']}%"
                        })
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, width='stretch')
                    
                    # Create bar chart
                    st.write("**Category Distribution:**")
                    chart_data = pd.DataFrame({
                        "Category": [cat for cat in summary["categories"].keys()],
                        "Percentage": [stats["percentage"] for stats in summary["categories"].values()]
                    })
                    
                    # Create Plotly bar chart
                    create_category_distribution_chart(chart_data)
                else:
                    st.session_state.breakdown_column = selected_breakdown
                    # Get summary statistics with breakdown
                    summary = get_categorisation_summary_with_breakdown(
                        result_df, selected_column, categories, selected_breakdown
                    )
                    
                    # Display summary statistics
                    st.write("**Summary Statistics:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Responses", summary["total_responses"])
                    with col2:
                        st.metric("Categories", len(categories))
                    with col3:
                        st.metric("Breakdown Values", len(summary["breakdown_values"]))
                    
                    # Create summary table with breakdown
                    summary_data = {"Category": []}
                    summary_data["Total Count"] = []
                    summary_data["Total %"] = []
                    
                    # Add columns for each breakdown value
                    for breakdown_value in summary["breakdown_values"]:
                        summary_data[f"{breakdown_value} Count"] = []
                        summary_data[f"{breakdown_value} %"] = []
                    
                    for category, stats in summary["categories"].items():
                        summary_data["Category"].append(category)
                        summary_data["Total Count"].append(stats["count"])
                        summary_data["Total %"].append(f"{stats['percentage']}%")
                        
                        for breakdown_value in summary["breakdown_values"]:
                            breakdown_stat = stats["breakdown"][breakdown_value]
                            summary_data[f"{breakdown_value} Count"].append(breakdown_stat["count"])
                            summary_data[f"{breakdown_value} %"].append(f"{breakdown_stat['percentage']}%")
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, width='stretch')
                    
                    # Create stacked bar chart
                    st.write("**Category Distribution (Stacked by " + selected_breakdown + "):**")
                    
                    # Prepare data for stacked chart
                    # Chart shows percentage of TOTAL sample who are in both category AND breakdown group
                    total_responses = summary["total_responses"]
                    chart_data = {"Category": [cat for cat in summary["categories"].keys()]}
                    index_data = {}  # Store index values for each segment
                    
                    for breakdown_value in summary["breakdown_values"]:
                        chart_data[breakdown_value] = []
                        index_data[breakdown_value] = []
                        for category in summary["categories"].keys():
                            breakdown_stat = summary["categories"][category]["breakdown"][breakdown_value]
                            category_percentage = summary["categories"][category]["percentage"]
                            
                            # Calculate percentage of total sample (not percentage within demographic)
                            percentage_of_total = (breakdown_stat["count"] / total_responses) * 100 if total_responses > 0 else 0
                            chart_data[breakdown_value].append(round(percentage_of_total, 1))
                            
                            # Calculate index: (percentage in breakdown group / percentage in total) * 100
                            # percentage_in_group = (count in group with category) / (total in group) * 100
                            # percentage_in_total = category_percentage
                            if breakdown_stat["total_in_group"] > 0 and category_percentage > 0:
                                percentage_in_group = (breakdown_stat["count"] / breakdown_stat["total_in_group"]) * 100
                                index = (percentage_in_group / category_percentage) * 100
                                index_data[breakdown_value].append(round(index, 0))
                            else:
                                index_data[breakdown_value].append(None)
                    
                    chart_df = pd.DataFrame(chart_data)
                    
                    # Create Plotly stacked bar chart
                    create_stacked_breakdown_chart(chart_df, summary["breakdown_values"], index_data)
                
                # Download button
                st.write("**Download Categorised Data:** – this will download your original data with the new categorisation columns added")
                
                # Create Excel file in memory
                from io import BytesIO
                output = BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='Categorised Data', index=False)
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                output.seek(0)
                
                # Get filename for download
                original_filename = st.session_state.get('input_filename', 'data')
                base_name = os.path.splitext(original_filename)[0]
                download_filename = f"{base_name}_categorised.xlsx"
                
                st.download_button(
                    label="📥 Download Categorised Data (Excel)",
                    data=output.getvalue(),
                    file_name=download_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Please select a text column and define categories to proceed.")
