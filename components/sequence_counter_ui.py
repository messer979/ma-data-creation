"""
UI components for sequence counter management
"""

import streamlit as st
from data_creation.sequence_counter_manager import SequenceCounterManager


def render_sequence_counter_toggle():
    """
    Render toggle switch for persistent sequence counters in sidebar
    """
    counter_manager = SequenceCounterManager(use_streamlit=True)
    
    # Initialize enabled state if not set
    if 'sequence_counters_enabled' not in st.session_state:
        st.session_state['sequence_counters_enabled'] = False
    
    # Toggle switch
    enabled = st.toggle(
        "Store Sequence Counter Values",
        value=st.session_state['sequence_counters_enabled'],
        help="Enable to persist sequence counter values across generation requests. Counters will continue incrementing until session is reset."
    )
    
    # Update counter manager and session state
    counter_manager.set_enabled(enabled)
    st.session_state['sequence_counters_enabled'] = enabled
    
    return enabled


def render_sequence_values_button(selected_template: str = None):
    """
    Render button to view sequence values
    
    Args:
        selected_template: Optional template name to filter by
        
    Returns:
        True if button was clicked
    """
    counter_manager = SequenceCounterManager(use_streamlit=True)
    
    if not counter_manager.is_enabled():
        return False
    
    # Button to view sequence values
    if st.button("🔢 Sequence Values", help="View current sequence counter values", use_container_width=True):
        return True
    
    return False


def render_sequence_values_modal(selected_template: str = None):
    """
    Render modal/popup to display sequence counter values
    
    Args:
        selected_template: Optional template name to filter by
    """
    counter_manager = SequenceCounterManager(use_streamlit=True)
    
    if not counter_manager.is_enabled():
        st.warning("⚠️ Persistent sequence counters are not enabled. Enable the toggle to view sequence values.")
        return
    
    # Get counters
    if selected_template:
        counters = counter_manager.get_template_counters(selected_template)
        title = f"Sequence Counter Values - {selected_template}"
    else:
        counters = counter_manager.get_all_counters()
        title = "Sequence Counter Values - All Templates"
    
    if not counters:
        st.info("ℹ️ No sequence counter values have been set yet. Generate some data to see counter values.")
        return
    
    # Display counters in a table
    if selected_template:
        # Simple format: field_name -> next_value
        st.subheader(title)
        st.markdown("---")
        
        # Create a DataFrame for better display
        import pandas as pd
        data = []
        for field_name, current_value in counters.items():
            next_value = counter_manager.get_next_counter(selected_template, field_name)
            data.append({
                "Attribute": field_name,
                "Current Value": current_value,
                "Next Value": next_value
            })
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Reset button for this template
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 Reset Counters for This Template", use_container_width=True):
                    counter_manager.reset_counters(selected_template)
                    st.success(f"✅ Sequence counters reset for '{selected_template}'")
                    st.rerun()
    else:
        # Group by template
        st.subheader(title)
        st.markdown("---")
        
        # Organize by template
        template_groups = {}
        for key, value in counters.items():
            if '::' in key:
                template, field = key.split('::', 1)
                if template not in template_groups:
                    template_groups[template] = {}
                template_groups[template][field] = value
        
        for template_name, template_counters in template_groups.items():
            with st.expander(f"📋 {template_name}", expanded=True):
                import pandas as pd
                data = []
                for field_name, current_value in template_counters.items():
                    next_value = counter_manager.get_next_counter(template_name, field_name)
                    data.append({
                        "Attribute": field_name,
                        "Current Value": current_value,
                        "Next Value": next_value
                    })
                
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Reset button for this template
                    if st.button(f"🔄 Reset {template_name}", key=f"reset_{template_name}"):
                        counter_manager.reset_counters(template_name)
                        st.success(f"✅ Sequence counters reset for '{template_name}'")
                        st.rerun()
        
        # Reset all button
        st.markdown("---")
        if st.button("🗑️ Reset All Counters", type="secondary", use_container_width=True):
            counter_manager.reset_counters()
            st.success("✅ All sequence counters reset")
            st.rerun()
