import streamlit as st
import time

st.write("This is a test page for debugging purposes.")

is_running = True

if 'count' not in st.session_state:
    st.session_state.count = 0
while is_running:
    st.write("The app is running. Click the button to stop it.")
    st.session_state.count += 1
    st.write(f"Current count: {st.session_state.count}")
    if st.button("Stop App"):
        is_running = False
        st.write("The app has been stopped.")
    
    st.write("You can add more debugging information here.")
    
    # Add a sleep to avoid busy-waiting
    time.sleep(2)
    st.rerun()