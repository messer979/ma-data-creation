import streamlit as st
from components.template_guide_modal import guide_modal

def render_sidebar():
    """
    Render the sidebar with configuration options (global and endpoint config only)
    """
    with st.sidebar:
        st.page_link('app.py', label='Data Creator', icon='🚀')
        st.page_link('pages/template_management.py', label='Template Management', icon='🗂️')
        st.page_link('pages/endpoint_management.py', label='Endpoint Management', icon='🔧')
        st.page_link('pages/inventory_import.py', label='Inventory Import', icon='📦')
        if st.button("❓ Help", help="Open Help Guide for Data Creation Tool"):
            guide_modal()
        st.markdown("---")
