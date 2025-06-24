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
    render_template_editor,
    render_bulk_template_manager_ui
)
from components.sidebar import render_sidebar
from data_creation.data_operations import handle_generate_button_click
import json
from dotenv import load_dotenv

load_dotenv()
# Page configuration
st.set_page_config(**PAGE_CONFIG)

dev_config_file = 'user_config.json'
# Initialize session state
if 'data_gen' not in st.session_state:
    st.session_state.data_gen = DataGenerator()

# Load config into session state at startup
load_initial_config_to_session()

def main():
    """Main Streamlit application with separated concerns"""
    # Title and description
    st.title("🚀 Rapid Active Data")
    st.markdown("Generate massive amounts of test data using JSON templates and send via API calls")
    theme = st.get_option("theme.base")
    try:
        # theme = st_theme()
        if theme == 'dark':
            st.session_state.ace_theme = "nord_dark"
        else:
            st.session_state.ace_theme = "github"
    except TypeError:
        st.session_state.ace_theme = "github"    # Render sidebar configuration
    render_sidebar()
    
    # Check if we should show the template manager page instead of main content
    if st.session_state.get('show_template_manager_page', False):
        # Render the bulk template manager UI which will handle the template manager page
        render_bulk_template_manager_ui(st.session_state.data_gen)
        return  # Exit early to avoid rendering main content
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
        
        if success:
            st.rerun()  # Refresh to show results      # Results panel at the bottom
    st.markdown("---")
    render_results_panel()
    
    # Footer
    st.markdown("---")
    st.markdown("Built with Streamlit • Modular Architecture • Template-Specific Endpoints")


if __name__ == "__main__":
    main()
