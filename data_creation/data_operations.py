"""
Data generation operations and business logic
"""

import json
import streamlit as st
from typing import List, Dict, Any
from data_creation.api_operations import send_data_to_api

def handle_generate_button_click(selected_template: str,
                                count: int,
                                template_params: Dict[str, Any],
                                send_to_api: bool,
                                batch_size: int,
                                template_editor_result: Dict[str, Any] = None) -> bool:
    """
    Handle the generate data button click logic
    
    Args:
        selected_template: Selected template name
        count: Number of records to generate
        template_params: Template-specific parameters
        send_to_api: Whether to send data to API
        batch_size: Batch size for API calls
        template_editor_result: Result from template editor with edited template and validation status
    
    Returns:
        bool: True if generation was successful, False otherwise
    """
    with st.spinner("Generating data..."):
        try:
            template_generator = st.session_state.data_gen.get_template_generator()
            
            # If template has been edited, use it for generation and save it if successful
            template_to_save = None
            if (template_editor_result and 
                template_editor_result.get('is_valid', False) and
                template_editor_result.get('template_changed', False)):
                
                # Update the in-memory template for generation
                editor_template = template_editor_result['template']
                template_generator.generation_templates[selected_template] = editor_template
                template_to_save = editor_template
            
            # Always use generation template system for data creation
            generated_data = st.session_state.data_gen.generate_data(
                selected_template, count, **template_params
            )
            
            # If generation was successful and we have a template to save, it's already saved above
            # No need to restore - keep the changes permanently
                
        except ValueError as e:
            st.error(f"❌ Error generating data: {str(e)}")
            st.info("Please check that the required template file exists in the 'templates' directory.")
            return False
        
        if generated_data:
            # Store in session state
            st.session_state.generated_data = generated_data
            st.session_state.data_type = selected_template
            
            # Show success message including template save confirmation if applicable
            success_msg = f"✅ Generated {len(generated_data)} records!"
            if template_to_save is not None:
                success_msg += " Template changes have been saved to session."
            st.success(success_msg)
              # Send to API if requested
            if send_to_api:
                # Get template-specific endpoint, headers, and configuration from session_state
                endpoints = st.session_state.get('user_endpoint_config', {})
                template_config = endpoints.get(selected_template, {})
                base_url = st.session_state.get('base_url', '')
                api_endpoint = base_url + template_config.get('endpoint', '/data')
                # Build headers
                headers = {
                    'Authorization': st.session_state.get('shared_token', ''),
                    'SelectedOrganization': st.session_state.get('selected_organization', ''),
                    'SelectedLocation': st.session_state.get('selected_location', ''),
                    'Content-Type': 'application/json'
                }
                api_results = send_data_to_api(
                    generated_data, 
                    api_endpoint, 
                    headers,
                    batch_size,
                    template_config
                )
                st.session_state.api_results = api_results
                return True
    
    return False


def extract_template_parameters(selected_template: str) -> Dict[str, Any]:
    """
    Extract template-specific parameters from Streamlit widgets
    
    Args:
        selected_template: Selected template name
    
    Returns:
        Dictionary of template parameters
    """
    params = {}
    
    if selected_template == 'facility':
        params['base_name'] = st.session_state.get('facility_base_name', 'STORE')
        
    elif selected_template == 'item':
        params['prefix'] = st.session_state.get('item_prefix', 'ITEM')
        
    elif selected_template == 'po':
        vendor_ids_input = st.session_state.get('vendor_ids_input', 'VENDOR001,VENDOR002')
        item_ids_input = st.session_state.get('item_ids_input', 'ITEM001,ITEM002')
        params['vendor_ids'] = [v.strip() for v in vendor_ids_input.split(',') if v.strip()]
        params['item_ids'] = [i.strip() for i in item_ids_input.split(',') if i.strip()]
        params['facility_id'] = st.session_state.get('facility_id', 'FACILITY01')
    
    return params
