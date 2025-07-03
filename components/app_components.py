"""
UI components and rendering functions for the Data Creation Tool
"""

import streamlit as st
from streamlit_ace import st_ace

import json
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from config import TEMPLATE_DEFAULTS, MAX_RECORDS, DEFAULT_RECORD_COUNT, DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE
from data_creation.api_operations import display_api_results
from components.template_guide_modal import guide_modal
from templates.bulk_template_manager import BulkTemplateManager




def render_template_selection(template_options: List[str]) -> str:
    """
    Render template selection dropdown
    
    Args:
        template_options: List of available template names
    
    Returns:
        Selected template name
    """
    if not template_options:
        st.error("No templates found! Please add JSON templates to the 'templates' directory.")
        return ""
      # Clean up template names for display
    display_options = [name.replace('_', ' ').title() for name in template_options]
    display_options.sort()  # Sort display options alphabetically
    selected_display = st.selectbox("Select Data Type", display_options)
    selected_template = template_options[display_options.index(selected_display)]
    
    return selected_template


def render_count_input() -> int:
    """
    Render the record count input
    
    Returns:
        Number of records to generate
    """
    return st.number_input(
        "Number of Records",
        min_value=1,
        max_value=MAX_RECORDS,
        value=DEFAULT_RECORD_COUNT,
        help=f"Number of records to generate (max {MAX_RECORDS:,})"
    )


def render_api_options():
    """
    Render API sending options
    
    Returns:
        Tuple of (send_to_api, batch_size)
    """
    st.subheader("API Options")
    send_to_api = st.checkbox("Send to API", value=False)
    batch_size = st.slider(
        "Batch Size", 
        min_value=1, 
        max_value=MAX_BATCH_SIZE, 
        value=DEFAULT_BATCH_SIZE, 
        help="Number of records per API call"
    )
    
    return send_to_api, batch_size


def render_data_preview(data: List[Dict[Any, Any]], data_type: str):
    """
    Render data preview and download options
    
    Args:
        data: Generated data to display
        data_type: Type of data for file naming
    """
    st.markdown(f"✅ Generated {len(data)} records")
    
    # Show first few records
    if data:
        # Add toggle for JSON viewer
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Preview Data (first 3 records)**")
        with col2:
            use_code_viewer = st.toggle("Use Code View", value=False, help="Toggle between simple JSON view and code view")
        
        with st.expander("Preview Data", expanded=True):
            for i, record in enumerate(data[:3]):
                if use_code_viewer:                    
                    st.markdown(f"**Record {i+1}:**")
                    st.code(json.dumps(record, indent=4), language="json", height=400)
                else:
                    st.json(record, expanded=2)
                  
                if i < 2 and i < len(data) - 1:
                    st.divider()          # Download All Data button
        # Create download button for complete dataset
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        full_data_json = json.dumps(data, indent=2)
        # st.download_button(
        #     label=f"📥 Download All Data ({len(data)} records)",
        #     data=full_data_json,
        #     file_name=f"{data_type}_complete_{len(data)}_{timestamp}.json",
        #     mime="application/json",
        #     use_container_width=True,
        #     help=f"Download all {len(data)} records as JSON file"
        # )
          # Download options
        st.subheader("💾 Download")
        
        # Create columns for side-by-side buttons
        col1, col2 = st.columns(2)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        
        # JSON download
        json_str = json.dumps(data, indent=2)
        
        with col1:
            st.download_button(
                label="📄 Download as JSON",
                data=json_str,
                file_name=f"{data_type}_{len(data)}_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
                
        with col2:
            # CSV download (if data can be flattened)
            try:
                if isinstance(data[0], dict):
                    df = pd.json_normalize(data)
                    csv_str = df.to_csv(index=False)
                    st.download_button(
                        label="📊 Download as CSV",
                        data=csv_str,
                        file_name=f"{data_type}_{len(data)}_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.button("📊 CSV Not Available", disabled=True, use_container_width=True, help="CSV download not available for this data structure")
            except Exception:
                st.button("📊 CSV Not Available", disabled=True, use_container_width=True, help="CSV download not available for this data structure")


def render_results_panel():
    """
    Render the results panel showing generated data and API results
    """
    st.header("📋 Results")
    # Display API results
    if 'api_results' in st.session_state:
        display_api_results(st.session_state.api_results)

    # Display generated data
    if 'generated_data' in st.session_state:
        data = st.session_state.generated_data
        data_type = st.session_state.get('data_type', 'data')
        render_data_preview(data, data_type)







def render_template_editor(data_gen, selected_template: str) -> Dict[str, Any]:
    """
    Render template editor for generation templates with JSON text area
    
    Args:
        data_gen: DataGenerator instance
        selected_template: Selected template name
    
    Returns:
        Dictionary containing edited generation template and validation status
    """
    st.subheader("🎛️ Generation Template Editor")
    
    # Get current generation template content
    template_generator = data_gen.get_template_generator()
    current_template = template_generator.get_template_info(selected_template)
    
    if current_template:
        template_json = json.dumps(current_template, indent=2)
    else:
        # Create a default generation template structure if none exists
        default_template = {
            "StaticFields": {},
            "SequenceFields": {},
            "RandomFields": [],
            "LinkedFields": {}
        }
        template_json = json.dumps(default_template, indent=2)
        current_template = default_template
    
    # Use separate session state keys for storing template content (not widget keys)
    content_key = f"template_content_{selected_template}"
    editor_key = f"generation_template_editor_{selected_template}"
        
    # Initialize the content storage if it doesn't exist
    if content_key not in st.session_state:
        st.session_state[content_key] = template_json
    
    # Get the current value for the editor (use stored content)
    editor_value = st.session_state.get(content_key, template_json)
    
    # JSON editor
    with st.expander("Edit Generation Template", expanded=True):
        edited_template = st_ace(
            value=editor_value,
            language="json",
            keybinding="sublime",
            height=500,
            key=editor_key,
            theme=st.session_state.ace_theme,
        )
        
        # Update the stored content when the editor changes
        if edited_template != editor_value:
            st.session_state[content_key] = edited_template
        
        # Validate JSON and generation template structure
        template_valid = True
        parsed_template = {}
        
        # Use the most current content from the editor
        current_editor_content = st.session_state.get(content_key, template_json)
        
        try:
            parsed_template = json.loads(current_editor_content)
            
            # Validate generation template structure
            required_sections = ["StaticFields", "SequenceFields", "RandomFields", "LinkedFields"]
            validation_errors = []
            
            for section in required_sections:
                if section not in parsed_template:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Validate RandomFields structure
            if "RandomFields" in parsed_template and isinstance(parsed_template["RandomFields"], list):
                for i, field in enumerate(parsed_template["RandomFields"]):
                    if not isinstance(field, dict) or "FieldName" not in field or "FieldType" not in field:
                        validation_errors.append(f"RandomFields[{i}] must have 'FieldName' and 'FieldType'")
            
            if validation_errors:
                st.error("❌ Generation template validation errors:")
                for error in validation_errors:
                    st.error(f"  • {error}")
                template_valid = False
                
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {e}")
            template_valid = False
    
    final_template = parsed_template if template_valid else current_template
    template_changed = template_valid and (json.dumps(parsed_template, sort_keys=True) != json.dumps(current_template, sort_keys=True))
    
    return {
        "template": final_template,
        "is_valid": template_valid,
        "template_changed": template_changed
    }


def _extract_field_paths(obj, prefix=""):
    """Extract all field paths from nested object using dot notation"""
    paths = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                paths.extend(_extract_field_paths(value, current_path))
            else:
                paths.append(current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{prefix}.{i}" if prefix else str(i)
            if isinstance(item, (dict, list)):
                paths.extend(_extract_field_paths(item, current_path))
            else:
                paths.append(current_path)
    
    return paths


