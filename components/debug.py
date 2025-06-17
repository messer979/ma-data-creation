import streamlit as st

def render_debug_section():
    """Render debug information for troubleshooting"""
    st.markdown("---")
    st.markdown("### 🔍 Debug Information")
    
    # Session state info
    with st.expander("Session State Contents", expanded=False):
        session_dict = {}
        for key in st.session_state.keys():
            value = getattr(st.session_state, key)
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                session_dict[key] = value
            else:
                session_dict[key] = {
                    "type": str(type(value).__name__),
                    "repr": str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                }
        st.json(session_dict)

