#!/usr/bin/env python3
"""
Data Creation Web Application
Generates massive amounts of test data using JSON templates via API calls
Built with Streamlit for a modern, interactive interface

Refactored version with separated concerns:
- UI components in ui_components.py
- Data operations in data_operations.py  
- API operations in api_operations.py
- Configuration in config.py
"""

import streamlit as st
from data_creation.data_generator import DataGenerator
from config import PAGE_CONFIG, load_initial_config_to_session
from components.app_components import (
    render_template_selection, 
    render_count_input,
    render_api_options,
    render_results_panel,
    render_template_editor
)
from components.sidebar import render_sidebar
from data_creation.data_operations import handle_generate_button_click
import json
from dotenv import load_dotenv
from data_creation.dev_config import is_dev_mode, get_dev_templates, load_env_config_if_dev_mode, load_dev_templates_to_generator


def _sync_generator_to_session_templates(template_generator):
    """
    Sync templates from the template generator to session state
    This ensures loaded templates are available in the editor
    
    Args:
        template_generator: TemplateGenerator instance with templates to sync
    """
    for template_name, template_content in template_generator.generation_templates.items():
        # Create session state key for this template
        content_key = f"template_content_{template_name}"
        
        # Convert template content to JSON string and store in session state
        try:
            template_json = json.dumps(template_content, indent=2)
            st.session_state[content_key] = template_json
        except Exception as e:
            print(f"Warning: Could not sync template {template_name} to session state: {e}")
            continue


# Page configuration
st.set_page_config(**PAGE_CONFIG)

dev_config_file = 'user_config.json'
# Initialize session state
if 'data_gen' not in st.session_state:
    st.session_state.data_gen = DataGenerator()
    # Sync any loaded generation templates to session state for the editor
    _sync_generator_to_session_templates(st.session_state.data_gen.get_template_generator())

# Load config into session state at startup
load_initial_config_to_session()


# Load dev templates if in dev mode
load_dev_templates_to_generator()
load_env_config_if_dev_mode()

def main():
    """Main Streamlit application with separated concerns"""
    # Title and description
    st.title("🚀 Rapid Active Data")
    st.markdown("Generate massive amounts of test data using JSON templates and send via API calls")
    render_sidebar()
    
      # Main content area (single column layout)
    # Template selection
    template_options = sorted(list(st.session_state.data_gen.get_template_generator().get_available_templates()))
    selected_template = render_template_selection(template_options)
    
    if not selected_template:
        return  # Exit if no templates available
    
    # Generation Template Editor
    template_editor_result = render_template_editor(
        st.session_state.data_gen,
        selected_template
    )
    
    st.markdown("---")
    
    # Count input
    count = render_count_input()
    
    # API options
    send_to_api, batch_size = render_api_options()
    
    # Generate button with separated logic
    col1, col2, col3 = st.columns([2, 2, 6])
    
    with col1:
        if st.button("🚀 Generate Data", type="primary"):
            # Check if template editor has valid results
            if not template_editor_result.get('is_valid', True):
                st.error("❌ Please fix the JSON template before generating data.")
                return
            
            success = handle_generate_button_click(
                selected_template=selected_template,
                count=count,
                template_params={},  # Empty dict since we removed template options
                send_to_api=send_to_api,
                batch_size=batch_size,
                template_editor_result=template_editor_result
            )
            
            # if success:
            #     st.rerun()  # Refresh to show results
    
    with col2:
        if st.button("🗑️ Clear Results", help="Clear all generated data and API results"):
            # Clear results from session state
            if 'generated_data' in st.session_state:
                del st.session_state['generated_data']
            if 'api_results' in st.session_state:
                del st.session_state['api_results']
            if 'data_type' in st.session_state:
                del st.session_state['data_type']
            st.success("✅ Results cleared!")
            st.rerun()
    
    # Empty column for spacing
    with col3:
        pass      # Results panel at the bottom
    st.markdown("---")
    render_results_panel()
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Modular Architecture • Template-Specific Endpoints")


if __name__ == "__main__":
    main()
