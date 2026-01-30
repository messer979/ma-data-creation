import streamlit as st
import json
from datetime import datetime
from components.template_guide_modal import guide_modal

def mark_config_updated():
    """Mark the configuration as updated with a timestamp"""
    if 'config_status_label' not in st.session_state:
        st.session_state['config_status_label'] = None
    
    timestamp = datetime.now().strftime("%I:%M %p")
    st.session_state['config_status_label'] = f"Updated at {timestamp}"

def render_sidebar():
    """
    Render the sidebar with configuration options (global and endpoint config only)
    """
    with st.sidebar:
        st.page_link('app.py', label='Data Creator', icon='🚀')
        st.page_link('pages/template_management.py', label='Template Management', icon='🗂️')
        st.page_link('pages/endpoint_management.py', label='Endpoint Management', icon='🔧')
        st.page_link('pages/inventory_import.py', label='Inventory Import', icon='📦')
        st.page_link('pages/order_import.py', label='Order Import', icon='🧾')
        st.page_link('pages/query_context.py', label='Query Context', icon='🔍')
        if st.button("❓ Help", help="Open Help Guide for Data Creation Tool"):
            guide_modal()
        
        st.markdown("---")
        
        # Sequence Counter Management
        from components.sequence_counter_ui import render_sequence_counter_toggle, render_sequence_values_button, render_sequence_values_modal
        
        st.markdown("### 🔢 Sequence Counters")
        enabled = render_sequence_counter_toggle()
        
        if enabled:
            # Show sequence values button if enabled
            if render_sequence_values_button():
                # Show modal with sequence values
                render_sequence_values_modal()
        
        st.markdown("---")
        
        # Initialize session state for tracking changes
        if 'last_config_export' not in st.session_state:
            st.session_state['last_config_export'] = None
        if 'config_status_label' not in st.session_state:
            st.session_state['config_status_label'] = None
        
        # Export full configuration button with status label
        col1, col2 = st.columns([3, 2])
        
        with col1:
            export_clicked = st.button("💾 Export Full Config", help="Export all endpoints, base templates, and generation templates", use_container_width=True)
        
        with col2:
            # Display status label
            if st.session_state['config_status_label']:
                if st.session_state['config_status_label'] == 'Saved':
                    st.markdown("✅ **Saved**")
                else:
                    st.markdown(f"🟡 {st.session_state['config_status_label']}")
        
        if export_clicked:
            # Prepare comprehensive export data
            export_data = {
                "metadata": {
                    "export_date": datetime.now().isoformat(),
                    "export_tool": "RAD - Full Configuration Export",
                    "description": "Complete export of endpoints and templates"
                },
                "environment": {
                    "base_url": st.session_state.get('base_url', ''),
                    "shared_token": st.session_state.get('shared_token', ''),
                    "selected_organization": st.session_state.get('selected_organization', ''),
                    "selected_location": st.session_state.get('selected_location', '')
                },
                "endpoints": {},
                "base_templates": [],
                "generation_templates": []
            }
            
            # Export endpoint configurations (correct key is 'user_endpoint_config')
            if 'user_endpoint_config' in st.session_state:
                export_data["endpoints"] = st.session_state['user_endpoint_config']
            
            # Export base templates (correct key is 'session_base_templates')
            if 'session_base_templates' in st.session_state:
                for template_name, template_content in st.session_state['session_base_templates'].items():
                    export_data["base_templates"].append({
                        "name": template_name,
                        "content": template_content
                    })
            
            # Export generation templates (correct key is 'session_generation_templates')
            if 'session_generation_templates' in st.session_state:
                for template_name, template_content in st.session_state['session_generation_templates'].items():
                    export_data["generation_templates"].append({
                        "name": template_name,
                        "content": template_content
                    })
            
            # Add counts to metadata
            export_data["metadata"]["endpoint_count"] = len(export_data["endpoints"])
            export_data["metadata"]["base_template_count"] = len(export_data["base_templates"])
            export_data["metadata"]["generation_template_count"] = len(export_data["generation_templates"])
            
            # Convert to JSON string
            json_str = json.dumps(export_data, indent=2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"full_config_export_{timestamp}.json"
            
            # Download button
            st.download_button(
                label="📥 Download Configuration",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
                help=f"Export {export_data['metadata']['endpoint_count']} endpoints, {export_data['metadata']['base_template_count']} base templates, {export_data['metadata']['generation_template_count']} generation templates"
            )
            
            # Mark as saved
            st.session_state['config_status_label'] = 'Saved'
            st.session_state['last_config_export'] = datetime.now()
        
        st.markdown("---")
