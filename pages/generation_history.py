"""
Template Generation History Page
Shows the history of template generations stored in the history database
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any

from components.sidebar import render_sidebar
from data_creation.history_db import get_history_db
from config import load_initial_config_to_session


def render_history_overview():
    """Render overview statistics and recent history"""
    st.header("📊 Generation History Overview")
    
    history_db = get_history_db()
    
    # Get usage statistics
    stats = history_db.get_template_usage_stats()
    
    if not stats:
        st.info("No generation history found yet. Start generating data to see history here!")
        return
    
    # Display statistics
    st.subheader("📈 Template Usage Statistics")
    
    # Convert to DataFrame for better display
    stats_df = pd.DataFrame(stats)
    
    # Create metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_generations = stats_df['usage_count'].sum()
        st.metric("Total Generations", total_generations)
    
    with col2:
        total_records = stats_df['total_records_generated'].sum()
        st.metric("Total Records Generated", f"{total_records:,}")
    
    with col3:
        unique_templates = len(stats_df)
        st.metric("Unique Templates Used", unique_templates)
    
    with col4:
        avg_records = stats_df['avg_records_per_generation'].mean()
        st.metric("Avg Records/Generation", f"{avg_records:.1f}")
    
    # Template usage table
    st.subheader("📋 Template Usage Details")
    
    # Format the data for display
    display_df = stats_df.copy()
    display_df['total_records_generated'] = display_df['total_records_generated'].apply(lambda x: f"{x:,}")
    display_df['avg_records_per_generation'] = display_df['avg_records_per_generation'].apply(lambda x: f"{x:.1f}")
    display_df['last_used'] = pd.to_datetime(display_df['last_used']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Rename columns for display
    display_df = display_df.rename(columns={
        'template_name': 'Template Name',
        'usage_count': 'Times Used',
        'total_records_generated': 'Total Records',
        'last_used': 'Last Used',
        'avg_records_per_generation': 'Avg Records/Gen'
    })
    
    st.dataframe(display_df, use_container_width=True)


def render_detailed_history():
    """Render detailed history with filters"""
    st.header("📝 Detailed Generation History")
    
    history_db = get_history_db()
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        # Template filter
        stats = history_db.get_template_usage_stats()
        template_names = ['All'] + [stat['template_name'] for stat in stats]
        selected_template = st.selectbox("Filter by Template", template_names)
    
    with col2:
        # Limit filter
        limit = st.number_input("Number of Records", min_value=10, max_value=1000, value=50, step=10)
    
    # Get history data
    template_filter = None if selected_template == 'All' else selected_template
    history_records = history_db.get_history(limit=limit, template_name=template_filter)
    
    if not history_records:
        st.info("No history records found for the selected filters.")
        return
    
    st.markdown(f"**Showing {len(history_records)} most recent records**")
    
    # Display history records
    for i, record in enumerate(history_records):
        with st.expander(
            f"🔄 {record['template_name']} - {record['record_count']} records - {record['generation_datetime'][:19]}",
            expanded=False
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Records Generated", record['record_count'])
            
            with col2:
                generation_time = datetime.fromisoformat(record['generation_datetime'])
                st.metric("Generation Time", generation_time.strftime('%Y-%m-%d %H:%M:%S'))
            
            with col3:
                created_time = datetime.fromisoformat(record['created_at'])
                st.metric("Saved to DB", created_time.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Template content
            st.markdown("**Template Content:**")
            try:
                template_content = json.loads(record['template_content'])
                st.json(template_content)
            except json.JSONDecodeError:
                st.code(record['template_content'], language='json')
            
            # Action buttons
            col1, col2, col3 = st.columns([2, 2, 6])
            
            with col1:
                # Copy template to clipboard (as text)
                template_text = json.dumps(json.loads(record['template_content']), indent=2)
                st.code(f"Template copied!", language='text')
                
            with col2:
                if st.button(f"🔄 Reuse Template", key=f"reuse_{record['id']}"):
                    # Store the template in session state for reuse
                    template_content = json.loads(record['template_content'])
                    st.session_state[f"template_content_{record['template_name']}"] = json.dumps(template_content, indent=2)
                    st.success(f"✅ Template loaded for {record['template_name']}!")


def render_history_management():
    """Render history management tools"""
    st.header("🔧 History Management")
    
    history_db = get_history_db()
    
    st.subheader("🗑️ Cleanup Old Records")
    st.markdown("Remove old history records to keep the database clean.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_old = st.number_input("Delete records older than (days)", min_value=1, max_value=365, value=30)
    
    with col2:
        if st.button("🗑️ Delete Old Records", type="secondary"):
            try:
                deleted_count = history_db.delete_old_records(days_old)
                if deleted_count > 0:
                    st.success(f"✅ Deleted {deleted_count} old records")
                else:
                    st.info("No old records found to delete")
            except Exception as e:
                st.error(f"❌ Error deleting records: {e}")
    
    st.divider()
    
    st.subheader("📤 Export History")
    st.markdown("Export your generation history for backup or analysis.")
    
    if st.button("📥 Export All History", type="secondary"):
        try:
            all_history = history_db.get_history(limit=10000)  # Large limit to get all
            if all_history:
                # Convert to DataFrame for CSV export
                df = pd.DataFrame(all_history)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download history.csv",
                    data=csv,
                    file_name=f"generation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No history to export")
        except Exception as e:
            st.error(f"❌ Error exporting history: {e}")


def main():
    """Main function for the History page"""
    # Configure page
    st.set_page_config(
        page_title="Generation History - RAD",
        page_icon="📊",
        layout="wide"
    )
    
    if not st.session_state.get('config_loaded', False):
        load_initial_config_to_session()
    
    # Render sidebar
    render_sidebar()
    
    # Page title
    st.title("📊 Template Generation History")
    st.markdown("Track and analyze your template generation activity over time.")
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📝 Detailed History", "🔧 Management"])
    
    with tab1:
        render_history_overview()
    
    with tab2:
        render_detailed_history()
    
    with tab3:
        render_history_management()


if __name__ == "__main__":
    main()
