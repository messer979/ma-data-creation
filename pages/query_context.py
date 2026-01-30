"""
Query Context Page
Allows users to execute SQL queries against the target environment to download data for context purposes.
The query results are stored as dataframes and made accessible for use in generation templates.
"""

import streamlit as st
import pandas as pd
import json
import requests
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from streamlit_ace import st_ace
import time 

from components.sidebar import render_sidebar
from components.wiretap import query_execution_wrapper
from config import load_initial_config_to_session
from data_creation.query_context_utils import load_csv_as_query


def load_dev_query_context() -> Dict[str, Any]:
    """
    Load queries from dev_query_context.json if it exists
    
    Returns:
        Dictionary containing queries or empty dict if file doesn't exist
    """
    try:
        dev_query_file = "dev_query_context.json"
        if os.path.exists(dev_query_file):
            with open(dev_query_file, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.warning(f"Error loading dev_query_context.json: {str(e)}")
        return {}


def get_query_by_name(query_name: str, dev_queries: List[Dict]) -> Optional[str]:
    """
    Get a specific query by name from the dev queries
    
    Args:
        query_name: Name of the query to find
        dev_queries: List of query dictionaries from dev_query_context.json
        
    Returns:
        SQL query string if found, None otherwise
    """
    for query in dev_queries:
        if query.get("name") == query_name:
            return query.get("query")
    return None
     
    

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


def render_csv_upload_interface():
    """Render the CSV upload interface"""
    st.subheader("📤 Upload CSV File")
    st.markdown("Upload a CSV file to use as query context data. This is useful for manual item data profiles or offline template generation.")
    
    # CSV file uploader
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file with your data profiles (e.g., item profiles, facility data, etc.)"
    )
    
    if uploaded_file is not None:
        # Query name input for CSV
        csv_query_name = st.text_input(
            "Query Name for CSV",
            value="",
            placeholder="Enter a name for this CSV data (e.g., 'item_profiles', 'facilities')",
            help="Give this CSV data a meaningful name to reference it in templates",
            key="csv_query_name"
        )
        
        col1, col2 = st.columns([2, 8])
        with col1:
            if st.button("📥 Load CSV as Query", type="primary", disabled=not csv_query_name.strip()):
                try:
                    # Save uploaded file temporarily
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    # Load CSV using the utility function
                    if load_csv_as_query(csv_query_name, tmp_file_path, source=f"CSV: {uploaded_file.name}"):
                        st.success(f"✅ CSV '{csv_query_name}' loaded successfully! {len(pd.read_csv(tmp_file_path))} rows loaded")
                        # Clean up temp file
                        os.unlink(tmp_file_path)
                        st.rerun()
                    else:
                        st.error("❌ Failed to load CSV file. Please check the file format.")
                        os.unlink(tmp_file_path)
                except Exception as e:
                    st.error(f"❌ Error loading CSV: {str(e)}")
                    if 'tmp_file_path' in locals():
                        try:
                            os.unlink(tmp_file_path)
                        except:
                            pass
        
        # Show preview if file is uploaded
        if uploaded_file is not None:
            try:
                df_preview = pd.read_csv(uploaded_file)
                st.markdown("**CSV Preview (first 5 rows):**")
                st.dataframe(df_preview.head(5), use_container_width=True)
                st.caption(f"Total rows: {len(df_preview)}, Columns: {', '.join(df_preview.columns.tolist()[:5])}{'...' if len(df_preview.columns) > 5 else ''}")
                # Reset file pointer for potential reload
                uploaded_file.seek(0)
            except Exception as e:
                st.error(f"Error reading CSV preview: {str(e)}")


def render_query_interface():
    """Render the main query interface"""
    st.header("🔍 Query Context Data")
    st.markdown("Execute SQL queries against your target environment or upload CSV files to gather context data for template generation.")
    
    # Create tabs for SQL Query and CSV Upload
    query_tab, csv_tab = st.tabs(["🔍 SQL Query", "📤 CSV Upload"])
    
    with query_tab:
        # Check if base URL is configured
        base_url = st.session_state.get('base_url', '')
        if not base_url:
            st.warning("⚠️ Base URL not configured. Please configure your base URL in the sidebar.")
        else:
            # Load dev queries
            dev_query_context = load_dev_query_context()
            if dev_query_context != {}:
                st.session_state['selected_query_name'] = dev_query_context['name']
                st.session_state['formatted_sql_value'] = dev_query_context['query']

            # Query input section
            st.subheader("📝 SQL Query")

            if 'formatted_sql_value' not in st.session_state:
                st.session_state['formatted_sql_value'] = "SELECT ii.ITEM_ID, ii.PROFILE_ID, ip.STANDARD, MAX(CASE WHEN ip.UOM_ID = 'units' THEN ip.QUANTITY END) AS UNITS_QUANTITY, MAX(CASE WHEN ip.UOM_ID = 'packs' THEN ip.QUANTITY END) AS PACKS_QUANTITY FROM default_item_master.ITE_ITEM ii INNER JOIN default_item_master.ITE_ITEM_PACKAGE ip ON ip.ITEM_PK = ii.PK AND ip.STANDARD = 1 GROUP BY ii.ITEM_ID limit 1000"
            
            # Query name input
            default_name = st.session_state.get('selected_query_name', 'items')
            query_name = st.text_input(
                "Query Name",
                value=default_name,
                placeholder="Enter a name for this query (e.g., 'active_facilities', 'available_items')",
                help="Give this query a meaningful name to reference it in templates"
            )
            
            # SQL Query text area
            current_sql_value = st.session_state['formatted_sql_value']
            sql_query = st_ace(
                value=current_sql_value,
                language='sql',
                theme=st.session_state.get('ace_theme', 'github'),
                height=200,
                auto_update=False,
                wrap=True,
                annotations=None,
                placeholder="Enter your SQL query here...",
                show_gutter=True,
                show_print_margin=True
            )

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
                    st.rerun()
    
    with csv_tab:
        render_csv_upload_interface()


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
        st.info("No query results stored yet. Execute a SQL query or upload a CSV file above to see results here.")
        return
    
    # Show summary of stored queries
    st.markdown(f"**{len(query_dataframes)} query result(s) available for template generation:**")
    
    for query_name, query_info in query_dataframes.items():
        # Determine source type for display
        source_type = query_info.get('source', 'API')
        source_label = "📤 CSV" if source_type.startswith('CSV') else "🔍 SQL"
        
        with st.expander(f"{source_label} {query_name} ({query_info['row_count']} rows)", expanded=False):
            df = query_info['dataframe']
            
            # Query metadata
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rows", query_info['row_count'])
            with col2:
                st.metric("Columns", len(query_info['columns']))
            with col3:
                # Handle both datetime objects and ISO strings
                created_at = query_info.get('created_at')
                if isinstance(created_at, str):
                    created_at_str = created_at
                elif hasattr(created_at, 'strftime'):
                    created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_at_str = str(created_at)
                st.caption(f"Created: {created_at_str}")
            with col4:
                if source_type.startswith('CSV'):
                    st.caption(f"Source: CSV File")
                else:
                    st.caption(f"Source: SQL Query")
            
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
    dev_query_context = load_dev_query_context()
    dev_queries = dev_query_context.get("queries", [])
    
    # Show information about dev queries if they exist
    if dev_queries:
        with st.expander("📋 Predefined Queries (dev_query_context.json)", expanded=False):
            st.markdown("The following queries are available from `dev_query_context.json`:")
            for query in dev_queries:
                st.markdown(f"**{query['name']}**")
                st.code(query['query'], language='sql')
                st.markdown("---")
    
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
