"""
Query Context Page
Allows users to execute SQL queries against the target environment to download data for context purposes.
The query results are stored as dataframes and made accessible for use in generation templates.
"""

import streamlit as st
import pandas as pd
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
from streamlit_ace import st_ace

from components.sidebar import render_sidebar
from components.wiretap import query_execution_wrapper
from config import load_initial_config_to_session
     
    

def store_query_result_as_dataframe(query_result: pd.DataFrame, query_name: str) -> bool:
    """
    Store query result as a pandas DataFrame in session state for use in templates
    
    Args:
        query_result: Result from execute_sql_query
        query_name: Name to store the DataFrame under
        
    Returns:
        True if successful, False otherwise
    """
    try:
        df = query_result

        # Store in session state under a specific key structure
        if 'query_dataframes' not in st.session_state:
            st.session_state['query_dataframes'] = {}
        print(f"Storing query result '{query_name}' with {len(df)} rows")
        st.session_state['query_dataframes'][query_name] = {
            'dataframe': df,
            'created_at': datetime.now(),
            'row_count': len(df),
            'columns': list(df.columns) if not df.empty else []
        }
        
        return True
        
    except Exception as e:
        st.error(f"Error storing query result: {str(e)}")
        return False


def render_query_interface():
    """Render the main query interface"""
    st.header("🔍 Query Context Data")
    st.markdown("Execute SQL queries against your target environment to gather context data for template generation.")
    
    # Check if base URL is configured
    base_url = st.session_state.get('base_url', '')
    if not base_url:
        st.warning("⚠️ Base URL not configured. Please configure your base URL in the sidebar.")
        return
    
    # Query input section
    st.subheader("📝 SQL Query")
    
    # Query name input
    query_name = st.text_input(
        "Query Name",
        value="items",
        placeholder="Enter a name for this query (e.g., 'active_facilities', 'available_items')",
        help="Give this query a meaningful name to reference it in templates"
    )
    
    # Get the current SQL value (either formatted or original)
    current_sql_value = st.session_state.get('formatted_sql_value', "SELECT ii.ITEM_ID, ii.PROFILE_ID, ip.STANDARD, MAX(CASE WHEN ip.UOM_ID = 'units' THEN ip.QUANTITY END) AS UNITS_QUANTITY, MAX(CASE WHEN ip.UOM_ID = 'packs' THEN ip.QUANTITY END) AS PACKS_QUANTITY FROM default_item_master.ITE_ITEM ii INNER JOIN default_item_master.ITE_ITEM_PACKAGE ip ON ip.ITEM_PK = ii.PK AND ip.STANDARD = 1 GROUP BY ii.ITEM_ID limit 1000")
    
    # SQL Query text area
    sql_query = st_ace(
        value=current_sql_value,
        language='sql',
        theme=st.session_state.get('ace_theme', 'github'),
        key="sql_query_editor",
        height=200,
        auto_update=False,
        wrap=True,
        annotations=None,
        placeholder="Enter your SQL query here...",
        show_gutter=True,
        show_print_margin=True
    )    
    # Update the current SQL value if user has typed in the editor
    if sql_query != current_sql_value:
        st.session_state['formatted_sql_value'] = sql_query
            
    # Execute button
    col1, col2, col3 = st.columns([2, 2, 6])
    organization = st.text_input(
        "Organization",
        value=st.session_state.get('selected_organization'),
        help="Organization ID for the query execution"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": st.session_state.get('shared_token', ''),
        "Organization": organization
    }

    with col1:
        if st.button("🚀 Execute Query", type="primary", disabled=not (sql_query.strip() and query_name.strip())):
            execute_query_workflow(sql_query, base_url, headers, query_name)
    
    with col2:
        if st.button("🗑️ Clear Results", help="Clear all stored query results"):
            if 'query_dataframes' in st.session_state:
                del st.session_state['query_dataframes']
            st.success("✅ Query results cleared!")


def execute_query_workflow(sql_query, base_url, headers, query_name):
    """Execute the complete query workflow"""
    try:
        # Show progress
        with st.spinner(f"Executing query '{query_name}'..."):
            # Execute the query
            result = query_execution_wrapper(base_url, headers, sql_query)

        if isinstance(result, pd.DataFrame):
            # Store as DataFrame
            if store_query_result_as_dataframe(result, query_name):
                st.success(f"✅ Query '{query_name}' executed successfully! {len(result)} rows retrieved")
            else:
                st.error("❌ Failed to store query results")
        else:
            st.error(f"❌ Query failed: {result}")
            
            # Show additional error details in an expander
            with st.expander("Error Details"):
                st.code(json.dumps(result, indent=2), language='json')
                
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")


def render_stored_queries():
    """Render the section showing stored query results"""
    st.subheader("📊 Stored Query Results")
    
    query_dataframes = st.session_state.get('query_dataframes', {})
    
    if not query_dataframes:
        st.info("No query results stored yet. Execute a query above to see results here.")
        return
    
    # Show summary of stored queries
    st.markdown(f"**{len(query_dataframes)} query result(s) available for template generation:**")
    
    for query_name, query_info in query_dataframes.items():
        with st.expander(f"📋 {query_name} ({query_info['row_count']} rows)", expanded=False):
            df = query_info['dataframe']
            
            # Query metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", query_info['row_count'])
            with col2:
                st.metric("Columns", len(query_info['columns']))
            with col3:
                st.caption(f"Created: {query_info['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Show column information
            if query_info['columns']:
                st.markdown("**Columns:**")
                st.code(", ".join(query_info['columns']))
            
            # Show data preview
            if not df.empty:
                st.markdown("**Data Preview (first 10 rows):**")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Download button for full dataset
                csv = df.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {query_name}.csv",
                    data=csv,
                    file_name=f"{query_name}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No data in this query result.")
            
            # Delete button
            if st.button(f"🗑️ Delete {query_name}", key=f"delete_{query_name}"):
                del st.session_state['query_dataframes'][query_name]
                st.success(f"✅ Deleted query result '{query_name}'")
                st.rerun()


def render_template_integration_guide():
    """Render guide on how to use query results in templates"""
    st.subheader("🔗 Using Query Results in Templates")
    
    query_dataframes = st.session_state.get('query_dataframes', {})
    
    if not query_dataframes:
        st.info("Execute queries above to see integration examples.")
        return
    
    st.markdown("""
    Query results are automatically available in your generation templates as pandas DataFrames. 
    You can reference them in your template logic to create context-aware data.
    """)
    
    # Show available queries
    query_names = list(query_dataframes.keys())
    if query_names:
        st.markdown("**Available Query Results:**")
        for query_name in query_names:
            info = query_dataframes[query_name]
            st.markdown(f"- `{query_name}` - {info['row_count']} rows with columns: {', '.join(info['columns'][:5])}{'...' if len(info['columns']) > 5 else ''}")
    
    # Show example usage
    with st.expander("💡 Example Template Usage"):
        st.markdown("""
        **Query Context Modes:**
        
        1. **Random Mode** - Select random values from a column:
        ```json
        "facility_id": {
            "query": "facilities",
            "column": "facility_id",
            "mode": "random"
        }
        ```
        
        2. **Unique Mode** - Select from unique values only:
        ```json
        "item_id": {
            "query": "items",
            "column": "item_id",
            "mode": "unique"
        }
        ```
        
        3. **Match Mode** - Lookup based on matching keys:
        ```json
        "OriginalOrderLine.OrderedQuantity": {
            "query": "items",
            "column": "PACKS_QUANTITY",
            "mode": "match",
            "template_key": "OriginalOrderLine.ItemId",
            "query_key": "ITEM_ID",
            "operation": "*(3,7)"
        }
        ```
        
        **Match Mode Explanation:**
        - `template_key`: Field in the template record to get the lookup value from
        - `query_key`: Column in the query dataframe to match against
        - `column`: Column in the query dataframe to get the result value from
        - `operation`: Optional math operation to apply to the result value
        
        **Supported Operations:**
        - `*5` - Multiply by 5
        - `*(1,5)` - Multiply by random integer between 1 and 5
        - `+10` - Add 10  
        - `+(5,15)` - Add random number between 5 and 15
        - `-3` - Subtract 3
        - `-(1,10)` - Subtract random number between 1 and 10
        - `/2` - Divide by 2
        - `/(2,5)` - Divide by random number between 2 and 5
        - `%100` - Modulo 100
        - `%(10,50)` - Modulo by random number between 10 and 50
        - `^2` or `**2` - Power of 2
        - `^(2,4)` or `**(2,4)` - Power of random number between 2 and 4
        
        Example: If ItemId = "KRITEM_001", find the row where ITEM_ID = "KRITEM_001", 
        get the PACKS_QUANTITY value from that row, then multiply by a random value between 3 and 7.
        """)
        
        if query_names:
            selected_query = st.selectbox("Select query for example:", query_names)
            if selected_query:
                info = query_dataframes[selected_query]
                columns = info['columns'][:3]  # Show first 3 columns
                
                st.markdown(f"**Example usage for '{selected_query}':**")
                st.code(f"""
# Get the {selected_query} query result
{selected_query}_df = get_query_dataframe('{selected_query}')

# Sample a random row
random_row = {selected_query}_df.sample(1)

# Extract values for template
template_data = {{
{chr(10).join([f'    "{col}": random_row["{col}"].iloc[0],' for col in columns])}
}}
                """, language='python')


def main():
    """Main function for the Query Context page"""
    # Configure page
    st.set_page_config(
        page_title="Query Context - RAD",
        page_icon="🔍",
        layout="wide"
    )
    if not st.session_state.get('config_loaded', False):
        load_initial_config_to_session()
    
    # Render sidebar
    render_sidebar()
    
    # Page title
    st.title("🔍 Query Context")
    st.markdown("Execute SQL queries to gather context data for intelligent template generation.")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📝 Execute Query", "📊 Stored Results", "🔗 Template Integration"])
    
    with tab1:
        render_query_interface()
    
    with tab2:
        render_stored_queries()
    
    with tab3:
        render_template_integration_guide()
    



if __name__ == "__main__":
    main()
