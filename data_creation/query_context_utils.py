"""
Query Context Utilities
Provides utility functions for accessing stored query results in template generation
"""

import pandas as pd
from typing import Optional, List, Dict, Any

# Handle Streamlit import gracefully for API mode
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Create a mock session state for API mode
    class MockSessionState:
        def __init__(self):
            self._data = {}
        def get(self, key, default=None):
            return self._data.get(key, default)
        def __setitem__(self, key, value):
            self._data[key] = value
        def __contains__(self, key):
            return key in self._data
        def __delitem__(self, key):
            if key in self._data:
                del self._data[key]
    st = type('MockStreamlit', (), {'session_state': MockSessionState()})()


def get_query_dataframe(query_name: str) -> Optional[pd.DataFrame]:
    """
    Get a stored query result DataFrame by name
    
    Args:
        query_name: Name of the stored query result
        
    Returns:
        pandas DataFrame if found, None otherwise
    """
    query_dataframes = st.session_state.get('query_dataframes', {})
    
    if query_name in query_dataframes:
        return query_dataframes[query_name]['dataframe']
    
    return None


def list_available_queries() -> List[str]:
    """
    Get a list of all available query result names
    
    Returns:
        List of query names
    """
    query_dataframes = st.session_state.get('query_dataframes', {})
    return list(query_dataframes.keys())


def get_query_info(query_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata information about a stored query result
    
    Args:
        query_name: Name of the stored query result
        
    Returns:
        Dictionary with query metadata (row_count, columns, created_at, etc.)
    """
    query_dataframes = st.session_state.get('query_dataframes', {})
    
    if query_name in query_dataframes:
        return query_dataframes[query_name]
    
    return None


def sample_from_query(query_name: str, n: int = 1) -> Optional[pd.DataFrame]:
    """
    Get a random sample from a stored query result
    
    Args:
        query_name: Name of the stored query result
        n: Number of rows to sample (default: 1)
        
    Returns:
        pandas DataFrame with sampled rows, None if query not found
    """
    df = get_query_dataframe(query_name)
    
    if df is not None and not df.empty:
        sample_size = min(n, len(df))
        return df.sample(sample_size)
    
    return None


def get_column_values(query_name: str, column_name: str) -> Optional[List[Any]]:
    """
    Get all values from a specific column in a stored query result
    
    Args:
        query_name: Name of the stored query result
        column_name: Name of the column to extract values from
        
    Returns:
        List of column values, None if query or column not found
    """
    df = get_query_dataframe(query_name)
    
    if df is not None and column_name in df.columns:
        return df[column_name].tolist()
    
    return None


def get_unique_column_values(query_name: str, column_name: str) -> Optional[List[Any]]:
    """
    Get unique values from a specific column in a stored query result
    
    Args:
        query_name: Name of the stored query result
        column_name: Name of the column to extract unique values from
        
    Returns:
        List of unique column values, None if query or column not found
    """
    df = get_query_dataframe(query_name)
    
    if df is not None and column_name in df.columns:
        return df[column_name].unique().tolist()
    
    return None


def filter_query_data(query_name: str, filters: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    Filter a stored query result based on column values
    
    Args:
        query_name: Name of the stored query result
        filters: Dictionary where keys are column names and values are the filter criteria
                Example: {'status': 'ACTIVE', 'type': 'WAREHOUSE'}
        
    Returns:
        Filtered pandas DataFrame, None if query not found
    """
    df = get_query_dataframe(query_name)
    
    if df is not None:
        filtered_df = df.copy()
        
        for column, value in filters.items():
            if column in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[column] == value]
        
        return filtered_df
    
    return None


def get_random_value_from_column(query_name: str, column_name: str) -> Optional[Any]:
    """
    Get a single random value from a specific column in a stored query result
    
    Args:
        query_name: Name of the stored query result
        column_name: Name of the column to sample from
        
    Returns:
        Random value from the column, None if query or column not found
    """
    df = get_query_dataframe(query_name)
    
    if df is not None and column_name in df.columns and not df.empty:
        return df[column_name].sample(1).iloc[0]
    
    return None


def query_exists(query_name: str) -> bool:
    """
    Check if a query result exists
    
    Args:
        query_name: Name of the query to check
        
    Returns:
        True if query exists, False otherwise
    """
    query_dataframes = st.session_state.get('query_dataframes', {})
    return query_name in query_dataframes


def get_query_summary() -> Dict[str, Dict[str, Any]]:
    """
    Get a summary of all stored query results
    
    Returns:
        Dictionary with query names as keys and summary info as values
    """
    query_dataframes = st.session_state.get('query_dataframes', {})
    summary = {}
    
    for query_name, query_info in query_dataframes.items():
        summary[query_name] = {
            'row_count': query_info['row_count'],
            'column_count': len(query_info['columns']),
            'columns': query_info['columns'],
            'created_at': query_info['created_at'],
            'query_time': query_info['query_time']
        }
    
    return summary


def load_csv_to_query_context(query_name: str, file_path: str) -> bool:
    """
    Load a CSV file into the query context as a DataFrame.
    
    Args:
        query_name: The name to assign to this query result.
        file_path: The path to the CSV file.
        
    Returns:
        True if successful, False otherwise.
    """
    if not os.path.exists(file_path):
        return False
    
    try:
        df = pd.read_csv(file_path)
        
        if 'query_dataframes' not in st.session_state:
            st.session_state['query_dataframes'] = {}
        
        from datetime import datetime
        st.session_state['query_dataframes'][query_name] = {
            'dataframe': df,
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': df.columns.tolist(),
            'created_at': datetime.now().isoformat(),
            'query_time': 0.0, # Not applicable for CSV load
            'source': f"CSV: {os.path.basename(file_path)}"
        }
        return True
    except Exception as e:
        # Handle CSV parsing errors
        return False


def load_csv_as_query(query_name: str, csv_file_path: str, source: str = "csv") -> bool:
    """
    ENHANCEMENT 4: Load a CSV file as a query result for use in QueryContextFields.
    This allows manual item data profiles to be uploaded instead of executing API queries.
    
    Args:
        query_name: Name to assign to this query result (used in QueryContextFields)
        csv_file_path: Path to the CSV file to load
        source: Source identifier (default: "csv")
    
    Returns:
        True if CSV loaded successfully, False otherwise
    """
    try:
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        
        # Initialize query_dataframes in session state if not exists
        if 'query_dataframes' not in st.session_state:
            st.session_state['query_dataframes'] = {}
        
        # Store the DataFrame with metadata (same structure as API queries)
        from datetime import datetime
        st.session_state['query_dataframes'][query_name] = {
            'dataframe': df,
            'row_count': len(df),
            'columns': list(df.columns),
            'created_at': datetime.now().isoformat(),
            'query_time': 0.0,  # CSV load time (could measure if needed)
            'source': source,
            'query': f"CSV: {csv_file_path}"  # Store source info
        }
        
        return True
    except Exception as e:
        # Log error but don't raise (could use logging)
        print(f"Error loading CSV as query '{query_name}': {str(e)}")
        return False