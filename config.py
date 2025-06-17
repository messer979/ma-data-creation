import streamlit as st
import json
"""
Configuration constants for the Data Creation Tool
"""

# API Configuration
DEFAULT_API_ENDPOINT = 'https://api.example.com/data'  # Replace with actual endpoint
DEFAULT_API_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_TOKEN'  # Replace with actual token
}

# App Configuration
PAGE_CONFIG = {
    'page_title': "Rapid Active Data",
    'page_icon': "🚀",
    'layout': "wide",
    'initial_sidebar_state': "expanded"
}

# Data Generation Limits
MAX_RECORDS = 100000
DEFAULT_RECORD_COUNT = 10
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000

# Template-specific defaults
TEMPLATE_DEFAULTS = {
    'facility': {'base_name': 'STORE'},
    'item': {'prefix': 'ITEM'},
    'po': {
        'vendor_ids': 'VENDOR001,VENDOR002',
        'item_ids': 'ITEM001,ITEM002',
        'facility_id': 'FACILITY01'
    }
}


def load_initial_config_to_session(config_file='configuration.json'):
    """Load initial config from file into session_state if not already loaded."""
    if not st.session_state.get('config_loaded', False):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                # Load endpoints
                endpoints = config_data.get('endpoints', {})
                st.session_state['user_endpoint_config'] = endpoints
                # Load environment/global settings
                st.session_state['base_url'] = config_data.get('base_url', '')
                headers = config_data.get('headers', {})
                st.session_state['shared_token'] = headers.get('Authorization', '')
                st.session_state['selected_organization'] = headers.get('SelectedOrganization', '')
                st.session_state['selected_location'] = headers.get('SelectedLocation', '')
            st.session_state['config_loaded'] = True
        except Exception as e:
            st.session_state['user_endpoint_config'] = {}
            st.warning(f"Could not load initial config: {e}")
