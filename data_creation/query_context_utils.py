"""
Query Context Utilities
Provides utility functions for accessing stored query results in template generation
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any


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
