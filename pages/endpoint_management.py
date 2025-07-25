#!/usr/bin/env python3
"""
Endpoint Management Page
Dedicated page for managing API endpoint configurations
"""

import json

import streamlit as st
from components.endpoint_config_ui import render_template_endpoint_config
from components.sidebar import render_sidebar
from config import load_initial_config_to_session
from components.debug import render_debug_section

# Page configuration
st.set_page_config(
    page_title="RAD: Endpoint Management",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main endpoint management page"""
    render_sidebar()
    
    st.title("🔧 Endpoint Management")
    st.markdown("Configure API endpoints, authentication, and payload settings for your data generation templates.")
    
    # Load .env configuration if dev mode is active
    
    # Ensure session state config exists
    if not st.session_state.get('config_loaded', False):
        load_initial_config_to_session()
    # Create two columns for better layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🌐 Environment Configuration")
        render_environment_configuration()
        
        st.markdown("---")
        render_import_export_section()
    
    with col2:
        st.markdown("### 📋 Template-Specific Configuration")
        render_template_configuration_section()
        
        # Debug section
        # render_debug_section()

def render_environment_configuration():
    """Render environment configuration settings (session_state only)"""
    with st.form("environment_config_form"):
        # Base URL
        base_url = st.session_state.get('base_url', '')
        new_base_url = st.text_input("Base URL", value=base_url, help="The base URL for all API endpoints")
        
        # Token
        token = st.session_state.get('shared_token', '')
        display_token = token.replace('Bearer ', '') if token.startswith('Bearer ') else token
        new_token = st.text_input("Bearer Token", value=display_token, type="password", help="Environment API token")
        
        # Organization
        org = st.session_state.get('selected_organization', '')
        new_org = st.text_input("Selected Organization", value=org, help="Organization value for API headers")
        
        # Facility
        facility = st.session_state.get('selected_location', '')
        new_facility = st.text_input("Selected Facility", value=facility, help="Facility value for API headers")
        
        # Form buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Environment Config", type="primary"):
                changed = False
                if new_base_url != base_url:
                    st.session_state['base_url'] = new_base_url
                    changed = True
                if new_token != display_token:
                    st.session_state['shared_token'] = f"Bearer {new_token}" if not new_token.startswith('Bearer ') else new_token
                    changed = True
                if new_org != org:
                    st.session_state['selected_organization'] = new_org
                    changed = True
                if new_facility != facility:
                    st.session_state['selected_location'] = new_facility
                    changed = True
                if changed:
                    st.success("✅ Environment configuration saved successfully!")
                    st.rerun()
                else:
                    st.info("ℹ️ No changes detected")
        
        with col2:
            if st.form_submit_button("🔄 Reset All", help="Reset all configurations to defaults"):
                for k in ['base_url', 'shared_token', 'selected_organization', 'selected_location']:
                    if k in st.session_state:
                        del st.session_state[k]
                if 'user_endpoint_config' in st.session_state:
                    del st.session_state['user_endpoint_config']
                st.success("All configurations reset to defaults!")
                st.rerun()

def render_template_configuration_section():
    """Render template-specific configuration section (session_state only)"""
    user_config = st.session_state.get('user_endpoint_config', {})
    available_templates = sorted(user_config.keys())
    if available_templates:
        selected_template = st.selectbox(
            "Select Template to Configure",
            available_templates,
            help="Choose a template to configure its specific endpoint settings"
        )
        
        if selected_template:
            st.markdown(f"#### Configure: {selected_template.replace('_', ' ').title()}")
            render_template_endpoint_config(selected_template)
    else:
        st.warning("No templates found. Please add templates to configure their endpoints.")

def render_import_export_section():
    """Render import/export configuration section (session_state only)"""
    # Export section
    st.markdown("#### 📤 Export Configuration")
    export_data = {
        "base_url": st.session_state.get('base_url', ''),
        "headers": {
            "Authorization": st.session_state.get('shared_token', ''),
            "SelectedOrganization": st.session_state.get('selected_organization', ''),
            "SelectedLocation": st.session_state.get('selected_location', ''),
            "Content-Type": "application/json"
        },
        "endpoints": st.session_state.get('user_endpoint_config', {})
    }
    st.download_button(
        label="💾 Download Full Config",
        data=json.dumps(export_data, indent=2),
        file_name="ma_data_creator_config.json",
        mime="application/json",
        help="Download the full configuration including all endpoints and environment settings"
    )
    
    # Import section
    st.markdown("#### 📥 Import Configuration")
    uploaded_file = st.file_uploader(
        "Choose config file",
        type=['json'],
        help="Upload a previously exported configuration file"
    )
    
    # Initialize session state for file processing tracking
    if "last_processed_file" not in st.session_state:
        st.session_state.last_processed_file = None

    if uploaded_file is not None:
        if st.session_state.last_processed_file != uploaded_file.file_id:
            try:
                config_content = uploaded_file.read().decode('utf-8')
                config_data = json.loads(config_content)
                
                # Load environment
                if 'base_url' in config_data:
                    st.session_state['base_url'] = config_data['base_url']
                if 'headers' in config_data:
                    headers = config_data['headers']
                    if 'Authorization' in headers:
                        st.session_state['shared_token'] = headers['Authorization']
                    if 'SelectedOrganization' in headers:
                        st.session_state['selected_organization'] = headers['SelectedOrganization']
                    if 'SelectedLocation' in headers:
                        st.session_state['selected_location'] = headers['SelectedLocation']
                # Load endpoints
                if 'endpoints' in config_data:
                    st.session_state['user_endpoint_config'] = config_data['endpoints']
                
                st.session_state.last_processed_file = uploaded_file.file_id
                
                st.success("✅ Configuration imported successfully!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file format")
            except Exception as e:
                st.error(f"❌ Error reading file: {e}")
        else:
            # File already processed, show status
            st.success("✅ Configuration imported successfully!")

if __name__ == "__main__":
    main()
