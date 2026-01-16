"""
API operations for sending data to external endpoints
"""

import streamlit as st
import time
from typing import List, Dict, Any

# Import development configuration utilities
from data_creation import dev_config


def send_data_to_api(generated_data: List[Dict[Any, Any]], 
                    api_endpoint: str, 
                    api_headers: Dict[str, str], 
                    batch_size: int,
                    template_config: Dict[str, Any] = None) -> List[Dict]:
    """
    Send generated data to API in batches with progress tracking
    
    Args:
        generated_data: List of records to send
        api_endpoint: API endpoint URL
        api_headers: Headers dictionary for the API request
        batch_size: Number of records per batch
        template_config: Template configuration dict containing 'type' and 'dataWrapper' fields
    
    Returns:
        List of batch results
    """
    api_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    response_text = st.empty()
    
    total_batches = (len(generated_data) + batch_size - 1) // batch_size
    for i in range(0, len(generated_data), batch_size):
        batch = generated_data[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        status_text.text(f"Sending batch {batch_num}/{total_batches}...")
        
        result = st.session_state.data_gen.send_to_api(
            batch, endpoint=api_endpoint, headers=api_headers, template_config=template_config
        )

        # Update status with response code
        status_code = result.get('status_code', 'N/A')
        response_text.text(f"Batch {batch_num}/{total_batches} - Response: {status_code}")
        
        api_results.append({
            'batch': batch_num,
            'size': len(batch),
            'result': result
        })
        
        progress_bar.progress(batch_num / total_batches)
        time.sleep(0.1)  # Small delay to show progress
    
    status_text.text("API calls completed!")
    
    # Show API results summary
    successful_batches = sum(1 for r in api_results if r['result']['success'])
    st.info(f"API Results: {successful_batches}/{len(api_results)} batches successful")
    
    return api_results


def display_api_results(api_results: List[Dict]):
    """
    Display API results in the UI
    
    Args:
        api_results: List of batch results from API calls
    """
    st.subheader("🌐 API Results")
    
    for result in api_results:
        batch_info = result['result']
        if batch_info['success']:
            api_success = batch_info['response']['success']
            status_code = batch_info['status_code']
            # Create expandable section for successful batches
            with st.expander(f"✅ Batch {result['batch']}: {result['size']} record(s) sent successfully. Status: <{status_code}> Success?: {api_success}", expanded=False):               
                # Show trace ID if available in response headers
                if 'response_headers' in batch_info and batch_info['response_headers']:
                    trace_id = batch_info['response_headers'].get('cp-trace-id')
                    if trace_id:
                        st.caption(f"Trace ID: {trace_id}")
                
                # Display the API response JSON - lazy load for performance
                if 'response' in batch_info:
                    st.subheader("API Response")
                    if batch_info['response']:
                        # Button to show/hide response details
                        show_response_key = f"show_response_{result['batch']}"
                        if show_response_key not in st.session_state:
                            st.session_state[show_response_key] = False
                        
                        if st.button("Show Response Details" if not st.session_state[show_response_key] else "Hide Response Details", key=f"btn_response_{result['batch']}"):
                            st.session_state[show_response_key] = not st.session_state[show_response_key]
                        
                        # Only render if user has clicked to show
                        if st.session_state[show_response_key]:
                            # Toggle switch for response view
                            show_as_code = st.toggle("Show as Code", value=False, help="Toggle between JSON tree view and code view", key=f"response_view_{result['batch']}")
                            
                            if show_as_code:
                                # Format and display the JSON response as code
                                import json
                                st.code(json.dumps(batch_info['response'], indent=2), language='json')
                            else:
                                # Display as interactive JSON tree (default)
                                st.json(batch_info['response'])
                    else:
                        st.info("No response body returned")
                else:
                    st.info("No response data available")
        else:
            status_code = batch_info.get('status_code', 'Unknown')
            error_msg = batch_info.get('error', 'Unknown error')
            
            # Create expandable section for failed batches
            with st.expander(f"❌ Batch {result['batch']}: {result['size']} record(s) failed. Status: <{status_code}> Error: {error_msg}", expanded=False):
                # Show detailed error information
                st.subheader("Error Details")
                
                # Display status code
                if batch_info.get('status_code'):
                    st.write(f"**Status Code:** {batch_info['status_code']}")
                
                # Display error message
                if batch_info.get('error'):
                    st.write(f"**Error:** {batch_info['error']}")
                
                # Show trace ID if available in response headers
                if 'response_headers' in batch_info and batch_info['response_headers']:
                    trace_id = batch_info['response_headers'].get('cp-trace-id')
                    if trace_id:
                        st.write(f"**Trace ID:** {trace_id}")
                
                # Create tabs for API response and request body
                tab1, tab2 = st.tabs(["API Error Response", "Request Body"])
                
                # Tab 1: API Error Response
                with tab1:
                    if 'response' in batch_info and batch_info['response']:
                        # Button to show/hide error response details
                        show_error_response_key = f"show_error_response_{result['batch']}"
                        if show_error_response_key not in st.session_state:
                            st.session_state[show_error_response_key] = False
                        
                        if st.button("Show Error Response" if not st.session_state[show_error_response_key] else "Hide Error Response", key=f"btn_error_response_{result['batch']}"):
                            st.session_state[show_error_response_key] = not st.session_state[show_error_response_key]
                        
                        # Only render if user has clicked to show
                        if st.session_state[show_error_response_key]:
                            # Toggle switch for response view
                            show_as_code = st.toggle("Show as Code", value=False, help="Toggle between JSON tree view and code view", key=f"error_response_view_{result['batch']}")
                            
                            if show_as_code:
                                # Format and display the JSON response as code
                                import json
                                st.code(json.dumps(batch_info['response'], indent=2), language='json')
                            else:
                                # Display as interactive JSON tree (default)
                                st.json(batch_info['response'])
                    elif 'response' in batch_info:
                        st.info("No response body returned")
                    else:
                        st.info("No response data available")
                
                # Tab 2: Request Body
                with tab2:
                    if 'request_body' in batch_info:
                        # Button to show/hide request body
                        show_request_key = f"show_request_{result['batch']}"
                        if show_request_key not in st.session_state:
                            st.session_state[show_request_key] = False
                        
                        if st.button("Show Request Body" if not st.session_state[show_request_key] else "Hide Request Body", key=f"btn_request_{result['batch']}"):
                            st.session_state[show_request_key] = not st.session_state[show_request_key]
                        
                        # Only render if user has clicked to show
                        if st.session_state[show_request_key]:
                            # Toggle switch for request view
                            show_request_as_code = st.toggle("Show as Code", value=False, help="Toggle between JSON tree view and code view", key=f"request_view_{result['batch']}")
                            
                            if show_request_as_code:
                                import json
                                st.code(json.dumps(batch_info['request_body'], indent=2), language='json')
                            else:
                                st.json(batch_info['request_body'])
                    else:
                        st.info("No request data available")


def get_dev_endpoints() -> Dict[str, Dict[str, Any]]:
    """
    Get development endpoints from .env configuration
    
    Returns:
        Dictionary of endpoint_name -> {url, headers} mappings
    """
    if not dev_config.is_dev_mode():
        return {}
    
    return dev_config.get_dev_endpoints()


def get_dev_endpoint_options() -> Dict[str, str]:
    """
    Get development endpoint options for UI dropdown
    
    Returns:
        Dictionary mapping display names to URLs
    """
    endpoints = get_dev_endpoints()
    return {name: config['url'] for name, config in endpoints.items()}


def get_endpoint_headers_by_name(endpoint_name: str) -> Dict[str, str]:
    """
    Get headers for a specific development endpoint
    
    Args:
        endpoint_name: Name of the endpoint from .env configuration
        
    Returns:
        Headers dictionary
    """
    endpoint_config = dev_config.get_endpoint_config(endpoint_name)
    if endpoint_config and 'headers' in endpoint_config:
        return endpoint_config['headers']
    return dev_config.get_default_headers()


def show_dev_config_info():
    """Display development configuration information in the UI"""
    if dev_config.is_dev_mode():
        st.sidebar.info("🔧 Development Mode Enabled")
        
        # Show available endpoints
        endpoints = get_dev_endpoints()
        if endpoints:
            with st.sidebar.expander("📡 Available Dev Endpoints"):
                for name, config in endpoints.items():
                    st.write(f"**{name}**: {config['url']}")
        
        # Show debug status
        if dev_config.is_debug_api_calls():
            st.sidebar.warning("🐛 API Debug Mode Active")
