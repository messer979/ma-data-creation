"""
UI components for managing endpoint configurations
"""

import streamlit as st
import json
from typing import Dict, Any
from config import load_initial_config_to_session


def render_template_endpoint_config(template_name: str, default_config: dict = None):
    """
    Render configuration form for a specific template with auto-update, using only session_state.
    Args:
        template_name: Name of the template to configure
        default_config: Optional default config for reset
    """
    st.markdown(f"**Configure: {template_name.replace('_', ' ').title()}**")



    user_config = st.session_state.get('user_endpoint_config', {})
    # Get current config for this template
    current_config = user_config.get(template_name, {})
    if not current_config and default_config:
        current_config = default_config.copy()

    # Create unique keys for this template's widgets
    endpoint_key = f"endpoint_{template_name}"
    type_key = f"type_{template_name}"
    wrapper_key = f"wrapper_{template_name}"
    desc_key = f"desc_{template_name}"

    endpoint = st.text_input(
        "Endpoint URL",
        value=current_config.get('endpoint', ''),
        help="The API endpoint URL for this template type",
        key=endpoint_key
    )

    type_options = ["none", "xint", "array"]
    current_type = current_config.get('type', 'none')
    selected_type = st.selectbox(
        "Payload Type",
        options=type_options,
        index=type_options.index(current_type) if current_type in type_options else 0,
        help="Type of payload wrapping:\n• 'xint' wraps in {\"Payload\": ...} for XINT endpoints\n• 'array' sends as array (same as none currently)\n• 'none' sends raw data without wrapper",
        key=type_key
    )
    data_wrapper = st.checkbox(
        "Data Wrapper",
        value=current_config.get('dataWrapper', False),
        help="When enabled, wraps records in {\"data\": [records]} structure",
        key=wrapper_key
    )
    st.markdown("**Payload Preview:**")
    if selected_type == 'xint' and data_wrapper:
        preview_text = '```json\n{"Payload": {"data": [records]}}\n```'
    elif selected_type == 'xint':
        preview_text = '```json\n{"Payload": [records]}\n```'
    elif data_wrapper:
        preview_text = '```json\n{"data": [records]}\n```'
    else:
        preview_text = '```json\n[records]\n```'
    st.markdown(preview_text)
    description = st.text_input(
        "Description",
        value=current_config.get('description', f'Endpoint for {template_name} data'),
        help="Description of this endpoint configuration",
        key=desc_key
    )
    # Update the current template config with the current values
    updated_config = {
        'endpoint': endpoint,
        'type': selected_type,
        'dataWrapper': data_wrapper,
        'description': description
    }
    if updated_config != st.session_state['user_endpoint_config'][template_name]:
        st.session_state['user_endpoint_config'][template_name] = updated_config
        st.rerun()

    # Reset button
    if st.button("🔄 Reset to Default", key=f"reset_{template_name}", help="Reset this template's configuration to default"):
        if default_config:
            st.session_state['user_endpoint_config'][template_name] = default_config.copy()
        else:
            if template_name in st.session_state['user_endpoint_config']:
                del st.session_state['user_endpoint_config'][template_name]
        st.success(f"Configuration reset to default for {template_name}!")
        st.rerun()