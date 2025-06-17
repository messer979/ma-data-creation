"""
API operations for sending data to external endpoints
"""

import streamlit as st
import time
from typing import List, Dict, Any


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
    
    total_batches = (len(generated_data) + batch_size - 1) // batch_size
    for i in range(0, len(generated_data), batch_size):
        batch = generated_data[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        status_text.text(f"Sending batch {batch_num}/{total_batches}...")
        
        result = st.session_state.data_gen.send_to_api(
            batch, endpoint=api_endpoint, headers=api_headers, template_config=template_config
        )

        
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
            # Create expandable section for successful batches
            with st.expander(f"✅ Batch {result['batch']}: {result['size']} records sent successfully", expanded=False):
                # Show response time if available
                if 'response_time' in batch_info:
                    st.caption(f"Response time: {batch_info['response_time']:.2f}s")
                
                # Show status code if available
                if 'status_code' in batch_info:
                    st.caption(f"Status code: {batch_info['status_code']}")
                
                # Show trace ID if available in response headers
                if 'response_headers' in batch_info and batch_info['response_headers']:
                    trace_id = batch_info['response_headers'].get('cp-trace-id')
                    if trace_id:
                        st.caption(f"Trace ID: {trace_id}")
                
                # Display the API response JSON
                if 'response' in batch_info:
                    st.subheader("API Response")
                    if batch_info['response']:
                        # Format and display the JSON response
                        import json
                        st.code(json.dumps(batch_info['response'], indent=2), language='json')
                    else:
                        st.info("No response body returned")
                else:
                    st.info("No response data available")
        else:
            st.error(f"❌ Batch {result['batch']}: {batch_info.get('error', 'Unknown error')}")
            if batch_info.get('status_code'):
                st.caption(f"Status code: {batch_info['status_code']}")
