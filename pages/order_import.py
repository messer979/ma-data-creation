"""
Order Import Page
Provides UI for importing order data including active inventory transfer functionality
"""

import streamlit as st
import json
import os
from datetime import datetime
from components.sidebar import render_sidebar
import uuid
from pandas import read_json
from dotenv import load_dotenv

load_dotenv()

# Production imports (commented out for testing)

from scripts.order_transfer_sync import run_transfer_sync

testing = os.getenv('TESTING', 'False').lower()
if testing == 'true':
    from_token_test = os.getenv('from_token_test')
    from_env_test = os.getenv('from_env_test')
    from_org_test = os.getenv('from_org_test')
    from_facility_test = os.getenv('from_facility_test')
    to_token_test = os.getenv('to_token_test')
    to_env_test = os.getenv('to_env_test')
    to_org_test = os.getenv('to_org_test')
    to_facility_test = os.getenv('to_facility_test')
else:
    from_token_test, from_env_test, from_org_test, from_facility_test, to_token_test, to_env_test, to_org_test, to_facility_test = (None,) * 8

# Use a unique log file per transfer (per user/session)
if 'transfer_log_uuid' not in st.session_state:
    st.session_state['transfer_log_uuid'] = None

# Initialize session state for form values
if 'form_from_env' not in st.session_state:
    st.session_state.form_from_env = from_env_test if testing else ""
if 'form_from_org' not in st.session_state:
    st.session_state.form_from_org = from_org_test if testing else ""
if 'form_from_facility' not in st.session_state:
    st.session_state.form_from_facility = from_facility_test if testing else ""
if 'form_from_token' not in st.session_state:
    st.session_state.form_from_token = from_token_test if testing else ""
if 'form_to_env' not in st.session_state:
    st.session_state.form_to_env = to_env_test if testing else ""
if 'form_to_org' not in st.session_state:
    st.session_state.form_to_org = to_org_test if testing else ""
if 'form_to_facility' not in st.session_state:
    st.session_state.form_to_facility = to_facility_test if testing else ""
if 'form_to_token' not in st.session_state:
    st.session_state.form_to_token = to_token_test if testing else ""
if 'form_attribute_type' not in st.session_state:
    st.session_state.form_attribute_type = "MinimumStatus"  # Default to MinimumStatus
if 'form_attribute_value' not in st.session_state:
    st.session_state.form_attribute_value = ""
if 'form_download_batch_size' not in st.session_state:
    st.session_state.form_download_batch_size = 200
if 'form_upload_batch_size' not in st.session_state:
    st.session_state.form_upload_batch_size = 50
if 'form_skip_items' not in st.session_state:
    st.session_state.form_skip_items = False
if 'form_skip_orders' not in st.session_state:
    st.session_state.form_skip_orders = False
if 'form_skip_facilities' not in st.session_state:
    st.session_state.form_skip_facilities = False

def get_log_file():
    uuid_val = st.session_state.get('transfer_log_uuid')
    if uuid_val:
        print(f'log exists transfer_status_{uuid_val}')
        return f"transfer_status_{uuid_val}.json"
    return None

st.set_page_config(page_title="RAD: Order Import", layout="wide", page_icon="🚀")
st.title("🧾 Order Import")
render_sidebar()

if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'transfer_log' not in st.session_state:
    st.session_state.transfer_log = []

# Create tabs for different import types

st.markdown("""
Transfer original orders between Manhattan Active WM environments.
This tool will:
1. Download order data from source environment
2. Transfer and sync items to target environment (unless "Skip items" is selected)
3. Transfer and sync facilities to target environment (unless "Skip Facilities" is selected)
4. Transfer and sync original orders to target environment (unless "Skip Orders" is selected)
""")

# Add validation warning for conflicting options
if st.session_state.get('form_skip_items', False) and st.session_state.get('form_skip_orders', False) and st.session_state.get('form_skip_facilities', False):
    st.warning("⚠️ Both 'Items only' and 'Inventory only' cannot be selected at the same time. Please choose one or neither.")

# Initialize session state for logging (must be outside form)
if 'transfer_running' not in st.session_state:
    st.session_state.transfer_running = False
if 'transfer_thread' not in st.session_state:
    st.session_state.transfer_thread = None
if 'previous_transfer_messages' not in st.session_state:
    st.session_state.previous_transfer_messages = []
    # Configuration form    
with st.form("inventory_config", enter_to_submit=False):
    st.subheader("📋 Configuration")
            
    # Test mode toggle
    # test_mode = st.checkbox("🧪 Test Mode (Use Dummy Server)", value=False, 
    #                        help="Use dummy server for testing UI without real API calls")
            
    col1, col2 = st.columns(2)
    token = ''
    with col1:
        st.markdown("**Source Environment**")
        from_env = st.text_input(
            "From Environment (Full URL)", 
            key="form_from_env",
            placeholder="clntv", 
            help="Source environment client subdomain, just 4 letter code plus env type")
        from_org = st.text_input(
            "From Organization", 
            key="form_from_org",
            placeholder="MA-DEV-L2", 
            help="Source organization code")
        from_facility = st.text_input(
            "From Facility", 
            key="form_from_facility",
            placeholder="DC01", 
            help="Source facility code")
        from_token = st.text_input(
            "From Token",
            key="form_from_token",
            placeholder="eyJhbG",
            help="Source environment API token")
    
    with col2:
        st.markdown("**Target Environment**")
        to_env = st.text_input(
            "To Environment (Full URL)", 
            key="form_to_env",
            placeholder="clnts", 
            help="Target environment client subdomain, just 4 letter code plus env type")
        to_org = st.text_input(
            "To Organization", 
            key="form_to_org",
            placeholder="MA-DEV-L2", 
            help="Target organization code")
        to_facility = st.text_input(
            "To Facility", 
            key="form_to_facility",
            placeholder="DC01", 
            help="Target facility code")
        to_token = st.text_input(
            "To Token", 
            key="form_to_token",
            placeholder="eyJhbG",
            help="Target environment API token")
    
    st.markdown("**Transfer Settings**")
    col3, col4, col5 = st.columns(3)
    
    with col3:
        # Find the current index for the selectbox
        options = ["MinimumStatus", "OrderType"]
        try:
            current_index = options.index(st.session_state.form_attribute_type)
        except ValueError:
            current_index = 0
        
        attribute_type = st.selectbox(
            "Filter By", 
            key="form_attribute_type",
            options=options,
            index=current_index,
            help="Select the type of attribute to filter inventory by"
        )
        attribute_value = st.text_input(
            f"Value", 
            key="form_attribute_value",
            placeholder=f"Enter {attribute_type} (e.g. SC, ZONE1, A01)", 
            value=st.session_state.form_attribute_value,
            help=f"Specific {attribute_type} value to filter inventory transfer"
        )
        print(f"Selected attribute type: {attribute_type}, value: {attribute_value}")

    
    with col4:
        download_batch_size = st.number_input("Download Batch Size", 
            key="form_download_batch_size",
            min_value=1, max_value=1000, 
            help="Records per download batch")        
        upload_batch_size = st.number_input("Upload Batch Size", 
            key="form_upload_batch_size",
            min_value=1, max_value=100,  
            help="Records per upload batch")
            
    with col5:
        st.markdown("**Transfer Options**")
        skip_items = st.checkbox(
            "Skip Items",
            key="form_skip_items", 
            value=st.session_state.form_skip_items,
            help="Skip item import"
        )
        skip_facilities = st.checkbox(
            "Skip Facilities", 
            key="form_skip_facilities",
            value=st.session_state.form_skip_facilities,
            help="Skip facility import"
        )        
        skip_orders = st.checkbox(
            "Skip Orders", 
            key="form_skip_orders",
            value=st.session_state.form_skip_orders,
            help="Skip order import"
        )        


    # Submit button
    prod_env = False
    # Validate prod env for 'p' at end of subdomain
    import re
    prod_pattern = r'https://[\w-]*p(?=\.)'
    if to_env:
        if re.search(prod_pattern, from_env) or re.search(prod_pattern, to_env):
            prod_env = True
            st.error("❌ Cannot use a production environment (subdomain ending in 'p') for source or target!")
    
    # Check for conflicting options
    conflicting_options = skip_items and skip_orders and skip_facilities
    if conflicting_options:
        st.error("❌ Cannot skip all imports!")
        
    can_submit = not prod_env and not conflicting_options and (all([
        from_env, from_org, from_facility, from_token,
        to_env, to_org, to_facility, to_token, attribute_value
    ]) or testing)
    if st.form_submit_button("🚀 Start Transfer", type="primary", use_container_width=True, disabled=not can_submit):
        # Store form values in session state
        st.session_state.submitted = True

# Handle form submission
if st.session_state.get('submitted', False):
    # Validate required fields
    required_fields = {
        'From Environment': from_env,
        'From Organization': from_org,
        'From Facility': from_facility,
        'From Token': from_token,
        'To Environment': to_env,
        'To Organization': to_org,
        'To Facility': to_facility,
        'To Token': to_token,
        f'{attribute_type.title()}': attribute_value}
    missing_fields = [name for name, value in required_fields.items() if not value]
    
    print('Missing fields:', missing_fields)
    if len(missing_fields) > 0:
        st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
    else:
        # Clear any previous transfer messages
        for msg in st.session_state.get('previous_transfer_messages', []):
            msg.empty()
        st.session_state.previous_transfer_messages = []
        
        st.session_state.transfer_running = True
        st.session_state.is_running = True
        
        # Show transfer starting info message
        transfer_info = st.info("🚀 Starting transfer... This may take some time. Please do not close this window.")
        
        # Generate a new UUID for this transfer and store in session_state
        transfer_uuid = str(uuid.uuid4())
        print(f"Starting transfer with UUID: {transfer_uuid}")
        st.session_state['transfer_log_uuid'] = transfer_uuid
        log_file = f"transfer_status_{transfer_uuid}.json"
        config = {
            'from_env': st.session_state.form_from_env,
            'from_org': st.session_state.form_from_org,
            'from_facility': st.session_state.form_from_facility,
            'from_token': st.session_state.form_from_token,
            'to_env': st.session_state.form_to_env,
            'to_org': st.session_state.form_to_org,
            'to_facility': st.session_state.form_to_facility,
            'to_token': st.session_state.form_to_token,
            'filter_type': st.session_state.form_attribute_type,
            'filter_value': st.session_state.form_attribute_value,
            'download_batch_size': st.session_state.form_download_batch_size,
            'upload_batch_size': st.session_state.form_upload_batch_size,
            'skip_items': st.session_state.form_skip_items,
            'skip_orders': st.session_state.form_skip_orders,
            'skip_facilities': st.session_state.form_skip_facilities,
        }
        
        
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

        # Create log display container
        log_container = st.container()
        log_placeholder = st.empty()
        
        def update_log_display(is_final=False):
            """Update the log display in real-time"""
            if log_file and os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        log_df = read_json(log_file, lines=True)
                    
                    if not log_df.empty:
                        # Filter columns for clarity if they exist
                        available_columns = log_df.columns.tolist()
                        preferred_columns = ['status', 'response_status', 'env', 'trace', 'timestamp', 'message']
                        display_columns = [col for col in preferred_columns if col in available_columns]
                        
                        if display_columns:
                            df = log_df[display_columns]
                        else:
                            df = log_df
                        
                        with log_placeholder.container():
                            if is_final:
                                st.subheader("📋 Transfer Log")
                                st.dataframe(df, use_container_width=True)  # Show all entries when final
                                # Add download button for final log
                                try:
                                    with open(log_file, "rb") as f:
                                        st.download_button(
                                            label="⬇️ Download Log File",
                                            data=f,
                                            file_name=os.path.basename(log_file),
                                            mime="application/json"
                                        )
                                except Exception as e:
                                    st.warning(f"Could not prepare log file for download: {str(e)}")
                            else:
                                st.subheader("📋 Live Transfer Log")
                                st.dataframe(df, use_container_width=True)  # Show last 10 entries during execution
                except Exception as e:
                    with log_placeholder.container():
                        st.warning(f"Could not read log file: {str(e)}")
        
        def progress_callback(message):
            """Callback to update progress in Streamlit"""
            status_text.text(message)
            # Update log display when progress changes
            update_log_display()
            # Note: progress_bar updates would need more sophisticated progress tracking
            # Run transfer directly
        
        try:
            # Show initial log display
            update_log_display()
            success = run_transfer_sync(config, log_file, progress_callback)
            if success:
                # Hide the transfer info message
                transfer_info.empty()
                success_msg = st.success("✅ Transfer completed successfully!")
                st.session_state.previous_transfer_messages.append(success_msg)
                progress_bar.progress(100)
                status_text.text("Transfer completed!")
                # Final log update - show complete log with download button
                update_log_display(is_final=True)
            else:
                # Hide the transfer info message
                transfer_info.empty()
                error_msg = st.error("❌ Transfer failed. Check logs for details.")
                st.session_state.previous_transfer_messages.append(error_msg)
                status_text.text("Transfer failed!")
                # Final log update - show complete log with download button
                update_log_display(is_final=True)
        except Exception as e:
            # Hide the transfer info message
            transfer_info.empty()
            error_msg = st.error(f"❌ Transfer error: {str(e)}")
            st.session_state.previous_transfer_messages.append(error_msg)
            status_text.text(f"Error: {str(e)}")
            # Final log update on error - show complete log with download button
            update_log_display(is_final=True)
        finally:
            st.session_state.transfer_running = False
            st.session_state.is_running = False
    # st.rerun()


# Add helpful information in sidebar
with st.sidebar:
    st.markdown("### 💡 Help & Tips")
    
    with st.expander("🔧 Environment Setup"):
        st.markdown("""
        **Environment Format**: Use short names like:
        - `dev01`, `test02`, `stage01`
        - Do not include full URLs
        
        **Tokens**: Use valid API tokens for each environment
        """)
    
    with st.expander("⚠️ Important Notes"):
        st.markdown("""
        - Cannot transfer TO production environments
        - Large transfers may take significant time
        - Monitor the log for progress and errors
        - Failed records are saved to 'Failed/' directory
        """)
    
    with st.expander("📊 Batch Size Guidelines"):
        st.markdown("""
        **Download Batch Size**: 
        - Recommended: 100-500
        - Higher = faster but more memory usage
        
        **Upload Batch Size**: 
        - Recommended: 25-100  
        - Lower = more reliable for large datasets
        - During inventory transfers, smaller batches may succeed if locations are missing
        """)

# Transfer log display for synchronous execution (only show if not currently running a transfer)

log_file = get_log_file()

# Only show the bottom log section if we're not currently running a transfer
# and if we don't have a recent transfer that just completed
if not st.session_state.get('submitted', False) and not st.session_state.get('transfer_running', False):
    # Show log if it exists
    if log_file and os.path.exists(log_file):
        st.subheader("📋 Transfer Log")
        
        # Refresh button for log display
        if st.button("🔄 Refresh Log"):
            st.rerun()
        
        # Display log content
        try:
            with open(log_file, 'r') as f:
                log_df = read_json(log_file, lines=True)
            
            if not log_df.empty:
                # Filter columns for clarity if they exist
                available_columns = log_df.columns.tolist()
                preferred_columns = ['timestamp', 'status', 'message', 'response_status']
                display_columns = [col for col in preferred_columns if col in available_columns]
                
                if display_columns:
                    df = log_df[display_columns]
                else:
                    df = log_df
                
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Log file is empty or still being written to...")
        except Exception as e:
            st.warning(f"Could not read log file: {str(e)}")
        
        # Download button for log file
        try:
            with open(log_file, "rb") as f:
                st.download_button(
                    label="⬇️ Download Log File",
                    data=f,
                    file_name=os.path.basename(log_file),
                    mime="application/json"
                )
        except Exception as e:
            st.warning(f"Could not prepare log file for download: {str(e)}")

    elif log_file:
        # Log file path exists but file doesn't exist yet
        st.info("Transfer log will appear here once the process starts generating logs...")
    elif st.session_state.get('transfer_log_uuid'):
        # We have a transfer UUID but no log file found
        st.warning("Log file not found. The transfer may still be starting up...")

