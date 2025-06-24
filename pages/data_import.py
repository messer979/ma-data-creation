"""
Data Import Page
Provides UI for importing data including active inventory transfer functionality
"""

import streamlit as st
import json
import os
from datetime import datetime
from components.sidebar import render_sidebar
import uuid
from pandas import read_json

# Production imports (commented out for testing)

# Test imports (functional only)
from celery_app import celery
from celery_app import run_transfer_task

testing = True
if testing:
    from_token_test = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyT3JncyI6WyJVU0FfREMiLCI5OTAwNCIsIjk5MDA1IiwiOTkwMTgiLCI5OTAwNyIsIjk5MDA2Il0sInVzZXJfbmFtZSI6ImNtZXNzZXJAbWFuaC5jb20iLCJ1c2VyTG9jYXRpb25zIjpbeyJsb2NhdGlvbklkIjoiOTkwMDQiLCJsb2NhdGlvblR5cGUiOiJkdW1teSJ9LHsibG9jYXRpb25JZCI6Ijk5MDA1IiwibG9jYXRpb25UeXBlIjoiZHVtbXkifSx7ImxvY2F0aW9uSWQiOiI5OTAxOCIsImxvY2F0aW9uVHlwZSI6ImR1bW15In0seyJsb2NhdGlvbklkIjoiOTkwMDciLCJsb2NhdGlvblR5cGUiOiJkdW1teSJ9LHsibG9jYXRpb25JZCI6Ijk5MDA2IiwibG9jYXRpb25UeXBlIjoiZHVtbXkifV0sImxvY2FsZSI6ImVuIiwiZXhjbHVkZWRVc2VyQnVzaW5lc3NVbml0cyI6W10sImF1dGhvcml0aWVzIjpbIlJPTEVfQ29ycF9BZG1pbiIsIlJPTEVfcmVwb3J0aW5nX2FkbWluIiwiUk9MRV9VU0VSIl0sImNsaWVudF9pZCI6Inp1dWxzZXJ2ZXIuMS4wLjAiLCJ1c2VyVGltZVpvbmUiOiJVUy9FYXN0ZXJuIiwiZWRnZSI6MCwic2NvcGUiOlsib21uaSJdLCJvcmdhbml6YXRpb24iOiJVU0FfREMiLCJhY2Nlc3N0b0FsbEJVcyI6ZmFsc2UsInRlbmFudElkIjoiZHRyZXN2cjExbyIsImV4cCI6MTc1MDgxMzQxMiwidXNlckRlZmF1bHRzIjpbeyJkZWZhdWx0TG9jYXRpb24iOiI5OTAxOCIsImRlZmF1bHRPcmdhbml6YXRpb24iOiI5OTAxOCIsImRlZmF1bHRCdXNpbmVzc1VuaXQiOm51bGx9XSwianRpIjoiNDYzYmI5YTAtOWE0Zi00MDYwLWI5MjItOGU5MDg5YTEyNzdiIiwidXNlckJ1c2luZXNzVW5pdHMiOltdfQ.AZYIXAsSZgVXUw15DU5w4QYrn8gDgNLKXCflW-7k85CESjJpQTFJLGKbO2HCt_EElYNF0M_k_bc0tw80I2uHcwJ7QAMS4f54LTVRLbLCIaOXiuMn2sjdMWrMSP7F9yaZH8hMOiTVOb6tt6kFQKqxw3FIoSVXyDAdAMRo0JYbeNF5b7oitpQajHV5ylLcwW0LrTnKTHCTq9edDXG4z992lp-88493-LSUzkZlvSA13O4EVEv-fuNshbVZ0IG_1QxqtuYbipq7-qZLwJITWtt9oi0LhPIWYvc8VywRL4gzjTbBpyCoDO1K7y9CnwslNhtOqP0IjM8vilBuFbvNi5keBg'
    from_env_test = 'https://dtrev.sce.manh.com'
    from_org_test = '99005'
    from_facility_test = '99005'

    to_token_test = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyT3JncyI6WyJVU0FfREMiLCI5OTAwNCIsIjk5MDA1IiwiOTkwMTgiLCI5OTAwNyIsIjk5MDA2Il0sInVzZXJfbmFtZSI6ImNtZXNzZXJAbWFuaC5jb20iLCJ1c2VyTG9jYXRpb25zIjpbeyJsb2NhdGlvbklkIjoiOTkwMDQiLCJsb2NhdGlvblR5cGUiOiJkdW1teSJ9LHsibG9jYXRpb25JZCI6Ijk5MDA1IiwibG9jYXRpb25UeXBlIjoiZHVtbXkifSx7ImxvY2F0aW9uSWQiOiI5OTAxOCIsImxvY2F0aW9uVHlwZSI6ImR1bW15In0seyJsb2NhdGlvbklkIjoiOTkwMDciLCJsb2NhdGlvblR5cGUiOiJkdW1teSJ9LHsibG9jYXRpb25JZCI6Ijk5MDA2IiwibG9jYXRpb25UeXBlIjoiZHVtbXkifV0sImxvY2FsZSI6ImVuIiwiZXhjbHVkZWRVc2VyQnVzaW5lc3NVbml0cyI6W10sImF1dGhvcml0aWVzIjpbIlJPTEVfQ29ycF9BZG1pbiIsIlJPTEVfcmVwb3J0aW5nX2FkbWluIiwiUk9MRV9VU0VSIl0sImNsaWVudF9pZCI6Inp1dWxzZXJ2ZXIuMS4wLjAiLCJ1c2VyVGltZVpvbmUiOiJVUy9FYXN0ZXJuIiwiZWRnZSI6MCwic2NvcGUiOlsib21uaSJdLCJvcmdhbml6YXRpb24iOiJVU0FfREMiLCJhY2Nlc3N0b0FsbEJVcyI6ZmFsc2UsInRlbmFudElkIjoiZHRyZXN2cjExbyIsImV4cCI6MTc1MDgxMzQxMiwidXNlckRlZmF1bHRzIjpbeyJkZWZhdWx0TG9jYXRpb24iOiI5OTAxOCIsImRlZmF1bHRPcmdhbml6YXRpb24iOiI5OTAxOCIsImRlZmF1bHRCdXNpbmVzc1VuaXQiOm51bGx9XSwianRpIjoiNDYzYmI5YTAtOWE0Zi00MDYwLWI5MjItOGU5MDg5YTEyNzdiIiwidXNlckJ1c2luZXNzVW5pdHMiOltdfQ.AZYIXAsSZgVXUw15DU5w4QYrn8gDgNLKXCflW-7k85CESjJpQTFJLGKbO2HCt_EElYNF0M_k_bc0tw80I2uHcwJ7QAMS4f54LTVRLbLCIaOXiuMn2sjdMWrMSP7F9yaZH8hMOiTVOb6tt6kFQKqxw3FIoSVXyDAdAMRo0JYbeNF5b7oitpQajHV5ylLcwW0LrTnKTHCTq9edDXG4z992lp-88493-LSUzkZlvSA13O4EVEv-fuNshbVZ0IG_1QxqtuYbipq7-qZLwJITWtt9oi0LhPIWYvc8VywRL4gzjTbBpyCoDO1K7y9CnwslNhtOqP0IjM8vilBuFbvNi5keBg'
    to_env_test = 'https://dtres.sce.manh.com'
    to_org_test = 'MANHD-005'
    to_facility_test = 'MANHD-005'
else:
    from_token, from_env, from_org, from_facility, to_token, to_env, to_org, to_facility = (None,) * 8

# Use a unique log file per transfer (per user/session)
if 'transfer_log_uuid' not in st.session_state:
    st.session_state['transfer_log_uuid'] = None

def get_log_file():
    uuid_val = st.session_state.get('transfer_log_uuid')
    if uuid_val:
        print(f'log exists transfer_status_{uuid_val}')
        return f"transfer_status_{uuid_val}.json"
    return None

LOG_FILE = "transfer_status.json"

st.set_page_config(page_title="Data Import", page_icon="📥")
st.title("📥 Data Import")
render_sidebar()

st.markdown("Import and transfer data between environments")

if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'transfer_log' not in st.session_state:
    st.session_state.transfer_log = []
if 'celery_task_id' not in st.session_state:
    st.session_state['celery_task_id'] = None

# Create tabs for different import types
tab1, tab2 = st.tabs(["🔄 Active Inventory Transfer", "📊 Bulk Data Import"])

with tab1:
    st.header("🔄 Active Inventory Transfer")
    st.markdown("""
    Transfer active inventory between Manhattan Active WM environments.
    This tool will:
    1. Download inventory data from source environment
    2. Transfer and sync items to target environment  
    3. Upload inventory adjustments to target environment    """)
    
    # Initialize session state for logging (must be outside form)
    if 'transfer_running' not in st.session_state:
        st.session_state.transfer_running = False
    if 'transfer_thread' not in st.session_state:
        st.session_state.transfer_thread = None
      # Configuration form
    with st.form("inventory_config"):
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
                value = from_env_test,
                placeholder="https://dev01.sce.ma.com", 
                help="Source environment full URL (e.g., https://dev01.sce.ma.com)")
            from_org = st.text_input(
                "From Organization", 
                value = from_org_test,
                placeholder="MA", 
                help="Source organization code")
            from_facility = st.text_input(
                "From Facility", 
                value = from_facility_test,
                placeholder="DC01", 
                help="Source facility code")
            from_token = st.text_input(
                "From Token",
                value = from_token_test,
                type="password", 
                help="Source environment API token")
        
        with col2:
            st.markdown("**Target Environment**")
            to_env = st.text_input(
                "To Environment (Full URL)", 
                value = to_env_test,
                placeholder="https://test01.sce.ma.com", 
                help="Target environment full URL (e.g., https://test01.sce.ma.com)")
            to_org = st.text_input(
                "To Organization", 
                value = to_org_test,
                placeholder="MA", 
                help="Target organization code")
            to_facility = st.text_input(
                "To Facility", 
                value = to_facility_test,
                placeholder="DC01", 
                help="Target facility code")
            to_token = st.text_input(
                "To Token", 
                value = to_token_test,
                type="password", 
                help="Target environment API token")
        
        st.markdown("**Transfer Settings**")
        col3, col4, col5 = st.columns(3)
        
        with col3:
            attribute_type = st.selectbox(
                "Filter By", 
                options=["Zone", "Area", "Aisle", "PickExecutionZoneId", "PickAllocationZoneId"],
                index=0,
                help="Select the type of attribute to filter inventory by"
            )
            attribute_value = st.text_input(
                f"{attribute_type.title()} Value", 
                placeholder=f"Enter {attribute_type} (e.g. SC, ZONE1, A01)", 
                value="",
                help=f"Specific {attribute_type} value to filter inventory transfer"
            )

        
        with col4:
            download_batch_size = st.number_input("Download Batch Size", min_value=1, max_value=1000, value=200, help="Records per download batch")        
        with col5:
            upload_batch_size = st.number_input("Upload Batch Size", min_value=1, max_value=100, value=10, help="Records per upload batch")        

        # Submit button
        prod_env = False
        # Validate prod env for 'p' at end of subdomain
        import re
        prod_pattern = r'https://[\w-]*p(?=\.)'
        if re.search(prod_pattern, from_env) or re.search(prod_pattern, to_env):
            prod_env = True
            st.error("❌ Cannot use a production environment (subdomain ending in 'p') for source or target!")
        can_submit = not prod_env and all([
            from_env, from_org, from_facility, from_token,
            to_env, to_org, to_facility, to_token, attribute_value
        ])
        if st.form_submit_button("🚀 Start Transfer", type="primary", use_container_width=True, disabled=not can_submit):
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
            f'{attribute_type.title()}': attribute_value
        }
        missing_fields = [name for name, value in required_fields.items() if not value]
        
        print('Missing fields:', missing_fields)
        if len(missing_fields) > 0:
            st.error(f"❌ Please fill in all required fields: {', '.join(missing_fields)}")
        else:
            st.session_state.transfer_running = True
            st.session_state.is_running = True
            # Generate a new UUID for this transfer and store in session_state
            transfer_uuid = str(uuid.uuid4())
            print(f"Starting transfer with UUID: {transfer_uuid}")
            st.session_state['transfer_log_uuid'] = transfer_uuid
            log_file = f"transfer_status_{transfer_uuid}.json"
            config = {
                'from_env': from_env,
                'from_org': from_org,
                'from_facility': from_facility,
                'from_token': from_token,
                'to_env': to_env,
                'to_org': to_org,
                'to_facility': to_facility,
                'to_token': to_token,
                'filter_type': attribute_type,
                'filter_value': attribute_value,
                'download_batch_size': download_batch_size,
                'upload_batch_size': upload_batch_size
            }
            async_result = run_transfer_task.apply_async(args=[config, log_file])
            st.session_state['celery_task_id'] = async_result.id
            print(f"Celery task started with ID: {async_result.id}")
            st.success("✅ Transfer started! Monitor progress below.")
            # st.rerun()

with tab2:
    st.header("📊 Bulk Data Import")
    st.markdown("*Coming soon - Additional bulk data import functionality*")
    
    st.info("This section will contain additional data import tools such as:")
    st.markdown("""
    - CSV file imports
    - JSON template imports
    - Database migrations
    - API data synchronization
    """)
    
    # Placeholder for future functionality
    uploaded_file = st.file_uploader("Choose a file to import", type=['csv', 'json', 'xlsx'])
    if uploaded_file:
        st.info("File upload functionality will be implemented here")

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
        """)

# Celery task monitoring and log display

celery_task_id = st.session_state.get('celery_task_id')
log_file = get_log_file()
if celery_task_id and log_file:
    async_result = celery.AsyncResult(celery_task_id)
    st.session_state.submitted = False
    st.write(f"Task state: {async_result.state}")
    # Show log file with refresh button
    st.subheader("📋 Transfer Log")
    if st.button("🔄 Refresh Log"):
        if os.path.exists(log_file):
            with open(log_file) as f:
                log_df = read_json(log_file, lines=True)
            df = log_df.filter(items=['timestamp', 'status', 'message', 'response_status'])  # Filter columns for clarity
            st.table(df)
        else:
            st.warning("Task still starting. Please wait...")
    if os.path.exists(log_file):
        with open(log_file, "rb") as f:
            st.download_button(
                label="⬇️ Download Log File",
                data=f,
                file_name=os.path.basename(log_file),
                mime="application/json"
            )

