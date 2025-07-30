import os
import json
import streamlit as st
from dotenv import dotenv_values


def is_dev_mode():
    config = dotenv_values('.env')
    return config.get('DEV_MODE', 'false').lower() == 'true'
    # """Check if development mode is enabled by checking if dev JSON files exist"""
    # return os.path.exists('dev_endpoints.json') or os.path.exists('dev_gen_templates.json')

def get_dev_endpoints():
    """Get development endpoints from dev_endpoints.json"""
    try:
        if os.path.exists('dev_endpoints.json'):
            with open('dev_endpoints.json', 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        pass
    return {}

def get_dev_templates():
    """Get development templates from dev_gen_templates.json"""
    try:
        if os.path.exists('dev_gen_templates.json'):
            with open('dev_gen_templates.json', 'r') as f:
                data = json.load(f)
                
                # Handle the structure with templates array
                if 'templates' in data and isinstance(data['templates'], list):
                    templates_dict = {}
                    for template_item in data['templates']:
                        if 'name' in template_item and 'content' in template_item:
                            templates_dict[template_item['name']] = template_item['content']
                    return templates_dict
                
                # Fallback: return as-is if different structure
                return data
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        pass
    return {}


def load_dev_endpoints():
    """Load configuration from dev JSON files using existing import methods if dev mode is active"""
    if not is_dev_mode():
        return
    
    # Only load once per session to avoid overriding user changes
    if st.session_state.get('dev_config_loaded', False):
        return
    
    dev_config_data = get_dev_endpoints()
    if not dev_config_data:
        return
    
    try:
        # Use the same logic as the existing import functionality
        # Load environment settings
        st.session_state['base_url'] = dev_config_data['base_url']

        headers = dev_config_data['headers']
        st.session_state['shared_token'] = headers['Authorization']
        st.session_state['selected_organization'] = headers.get('SelectedOrganization', '')
        st.session_state['selected_location'] = headers.get('SelectedLocation', '')
        # Load endpoints using existing import logic
        st.session_state['user_endpoint_config'] = dev_config_data['endpoints']
        
        # Load development templates into session state
        st.session_state['dev_config_loaded'] = True
                    
    except Exception as e:
        st.sidebar.error(f"Error loading dev config: {e}")
        
def load_dev_gen_templates():
    """
    Load templates from dev_gen_templates.json to the data generator if in dev mode
    """
    if not is_dev_mode():
        return
    
    # Only load once per session to avoid overriding user changes
    if st.session_state.get('dev_templates_loaded_to_generator', False):
        return
    
    dev_templates = get_dev_templates()
    if not dev_templates:
        return
    
    try:
        # Add templates to the data generator
        if 'data_gen' in st.session_state:
            template_generator = st.session_state.data_gen.get_template_generator()
            
            # Add each template directly to the generator's session state templates
            for template_name, template_content in dev_templates.items():
                # Access the session state key directly
                if template_generator.session_key in st.session_state:
                    st.session_state[template_generator.session_key][template_name] = template_content
                
                # Also create content key for editor
                content_key = f"template_content_{template_name}"
                try:
                    template_json = json.dumps(template_content, indent=2)
                    st.session_state[content_key] = template_json
                except Exception as e:
                    continue
            
        # Mark as loaded to prevent re-loading
        st.session_state['dev_templates_loaded_to_generator'] = True
        
        # Show notification if not shown already in another page
        if dev_templates and not st.session_state.get('dev_templates_notification_shown', False):
            st.sidebar.info(f"🔧 Dev mode: Loaded {len(dev_templates)} templates from JSON file")
            st.session_state['dev_templates_notification_shown'] = True
            
    except Exception as e:
        st.sidebar.error(f"Error loading dev templates to generator: {e}")
