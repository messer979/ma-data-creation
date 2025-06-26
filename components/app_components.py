"""
UI components and rendering functions for the Data Creation Tool
"""

import streamlit as st
from streamlit_ace import st_ace

import json
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from config import TEMPLATE_DEFAULTS, MAX_RECORDS, DEFAULT_RECORD_COUNT, DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE
from data_creation.api_operations import display_api_results
from components.template_guide_modal import guide_modal
from templates.bulk_template_manager import BulkTemplateManager




def render_template_selection(template_options: List[str]) -> str:
    """
    Render template selection dropdown
    
    Args:
        template_options: List of available template names
    
    Returns:
        Selected template name
    """
    if not template_options:
        st.error("No templates found! Please add JSON templates to the 'templates' directory.")
        return ""
      # Clean up template names for display
    display_options = [name.replace('_', ' ').title() for name in template_options]
    display_options.sort()  # Sort display options alphabetically
    selected_display = st.selectbox("Select Data Type", display_options)
    selected_template = template_options[display_options.index(selected_display)]
    
    return selected_template


def render_count_input() -> int:
    """
    Render the record count input
    
    Returns:
        Number of records to generate
    """
    return st.number_input(
        "Number of Records",
        min_value=1,
        max_value=MAX_RECORDS,
        value=DEFAULT_RECORD_COUNT,
        help=f"Number of records to generate (max {MAX_RECORDS:,})"
    )


def render_api_options():
    """
    Render API sending options
    
    Returns:
        Tuple of (send_to_api, batch_size)
    """
    st.subheader("API Options")
    send_to_api = st.checkbox("Send to API", value=False)
    batch_size = st.slider(
        "Batch Size", 
        min_value=1, 
        max_value=MAX_BATCH_SIZE, 
        value=DEFAULT_BATCH_SIZE, 
        help="Number of records per API call"
    )
    
    return send_to_api, batch_size


def render_data_preview(data: List[Dict[Any, Any]], data_type: str):
    """
    Render data preview and download options
    
    Args:
        data: Generated data to display
        data_type: Type of data for file naming
    """
    st.markdown(f"✅ Generated {len(data)} records")
    
    # Show first few records
    if data:
        # Add toggle for JSON viewer
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Preview Data (first 3 records)**")
        with col2:
            use_code_viewer = st.toggle("Use Code View", value=False, help="Toggle between simple JSON view and code view")
        
        with st.expander("Preview Data", expanded=True):
            for i, record in enumerate(data[:3]):
                if use_code_viewer:                    
                    st.markdown(f"**Record {i+1}:**")
                    st.code(json.dumps(record, indent=4), language="json", height=400)
                else:
                    st.json(record, expanded=2)
                  
                if i < 2 and i < len(data) - 1:
                    st.divider()          # Download All Data button
        # Create download button for complete dataset
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        full_data_json = json.dumps(data, indent=2)
        # st.download_button(
        #     label=f"📥 Download All Data ({len(data)} records)",
        #     data=full_data_json,
        #     file_name=f"{data_type}_complete_{len(data)}_{timestamp}.json",
        #     mime="application/json",
        #     use_container_width=True,
        #     help=f"Download all {len(data)} records as JSON file"
        # )
          # Download options
        st.subheader("💾 Download")
        
        # Create columns for side-by-side buttons
        col1, col2 = st.columns(2)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%y%m%d%H%M%S")
        
        # JSON download
        json_str = json.dumps(data, indent=2)
        
        with col1:
            st.download_button(
                label="📄 Download as JSON",
                data=json_str,
                file_name=f"{data_type}_{len(data)}_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
                
        with col2:
            # CSV download (if data can be flattened)
            try:
                if isinstance(data[0], dict):
                    df = pd.json_normalize(data)
                    csv_str = df.to_csv(index=False)
                    st.download_button(
                        label="📊 Download as CSV",
                        data=csv_str,
                        file_name=f"{data_type}_{len(data)}_{timestamp}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.button("📊 CSV Not Available", disabled=True, use_container_width=True, help="CSV download not available for this data structure")
            except Exception:
                st.button("📊 CSV Not Available", disabled=True, use_container_width=True, help="CSV download not available for this data structure")


def render_results_panel():
    """
    Render the results panel showing generated data and API results
    """
    st.header("📋 Results")
    # Display API results
    if 'api_results' in st.session_state:
        display_api_results(st.session_state.api_results)

    # Display generated data
    if 'generated_data' in st.session_state:
        data = st.session_state.generated_data
        data_type = st.session_state.get('data_type', 'data')
        render_data_preview(data, data_type)


def render_bulk_template_manager_ui(data_gen):
    """
    Render the bulk template manager interface based on session state
    
    Args:
        data_gen: DataGenerator instance
    """
    # Get the template generator
    template_generator = data_gen.get_template_generator()
    
    # Check if we should show the template manager page
    if st.session_state.get('show_template_manager_page', False):
        render_template_manager_page(template_generator)
    
    # Legacy support for existing bulk manager states
    elif st.session_state.get('show_bulk_manager', False):
        st.markdown("---")
        BulkTemplateManager.render_bulk_template_manager(template_generator)
        
        # Add close button
        if st.button("❌ Close Bulk Manager", help="Close bulk template manager"):
            st.session_state.show_bulk_manager = False
            st.rerun()
    
    elif st.session_state.get('show_bulk_export', False):
        st.markdown("---")
        render_bulk_export_ui(template_generator)
        
    elif st.session_state.get('show_bulk_import', False):
        st.markdown("---")
        render_bulk_import_ui(template_generator)


def render_template_manager_page(template_generator):
    """
    Render the dedicated template management page
    
    Args:
        template_generator: TemplateGenerator instance
    """
    # Clear the main content area and show template manager
    st.markdown("---")
    
    # Header with back button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Back to Main", help="Return to main data generation page"):
            st.session_state.show_template_manager_page = False
            st.rerun()
    
    with col2:
        st.title("🛠️ Template Manager")
    
    st.markdown("\n")
    
    # Render the full bulk template manager interface
    BulkTemplateManager.render_bulk_template_manager(template_generator)


def render_bulk_export_ui(template_generator):
    """
    Render the bulk export UI
    
    Args:
        template_generator: TemplateGenerator instance
    """
    st.subheader("📤 Export All Templates")
    
    if template_generator.generation_templates:
        st.write(f"Export all {len(template_generator.generation_templates)} generation templates as a single JSON file.")
        
        # Show template list
        with st.expander("📋 Templates to Export", expanded=False):
            for template_name in sorted(template_generator.generation_templates.keys()):
                st.write(f"• {template_name}")
          # Export and download button
        col1, col2 = st.columns([3, 1])
        with col1:
            # Generate export data
            json_str, export_data = BulkTemplateManager.export_all_templates(template_generator)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generation_templates_export_{timestamp}.json"
            
            # Single button that instantly downloads
            st.download_button(
                label="📥 Export & Download Templates",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
                help=f"Export and download all {len(template_generator.generation_templates)} templates instantly"
            )
            
            # Show export summary
            st.info(f"📋 Ready to export: {export_data['metadata']['template_count']} templates")
        
        with col2:
            if st.button("❌ Close", help="Close export interface"):
                st.session_state.show_bulk_export = False
                st.rerun()
    else:
        st.warning("No templates found to export.")
        if st.button("❌ Close", help="Close export interface"):
            st.session_state.show_bulk_export = False
            st.rerun()


def render_bulk_import_ui(template_generator):
    """
    Render the bulk import UI
    
    Args:
        template_generator: TemplateGenerator instance
    """
    st.subheader("📥 Import Templates")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Import generation templates from a JSON file.", 
        type=['json'],
        help="Upload a JSON file containing generation templates",
        key="bulk_import_file"
    )
        
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if uploaded_file is not None:
            try:
                # Read the uploaded file
                content = uploaded_file.read().decode('utf-8')
                
                # Preview the import
                try:
                    parsed_preview = json.loads(content)
                    if "templates" in parsed_preview and isinstance(parsed_preview["templates"], list):
                        st.info(f"📋 Ready to import {len(parsed_preview['templates'])} templates")
                        
                        # Show template names
                        with st.expander("🔍 Preview Templates", expanded=True):
                            for template in parsed_preview["templates"]:
                                if isinstance(template, dict) and "name" in template:
                                    exists = template["name"] in template_generator.generation_templates
                                    status = "⚠️ Will overwrite" if exists else "⚠️ Will skip" if exists else "✅ New"
                                    st.write(f"• {template['name']} {status}")
                    else:
                        st.error("Invalid template format")
                        uploaded_file = None
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
                    uploaded_file = None
                
                # Import button
                if uploaded_file is not None:
                    if st.button("🔼 Import Templates", use_container_width=True):
                        success, message, imported, skipped = BulkTemplateManager.import_all_templates(
                            template_generator, content
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            
                            if imported:
                                with st.expander("✅ Imported Templates", expanded=True):
                                    for template_name in imported:
                                        st.write(f"• {template_name}")
                            
                            if skipped:
                                with st.expander("⚠️ Skipped Templates", expanded=False):
                                    for template_name in skipped:
                                        st.write(f"• {template_name}")
                            
                            # Refresh the page to show new templates
                            if imported:
                                st.balloons()
                                st.rerun()
                        else:
                            st.error(f"❌ {message}")
                            
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    with col2:
        if st.button("❌ Close", help="Close import interface"):
            st.session_state.show_bulk_import = False
            st.rerun()
    


def render_template_editor(data_gen, selected_template: str) -> Dict[str, Any]:
    """
    Render template editor for generation templates with JSON text area
    
    Args:
        data_gen: DataGenerator instance
        selected_template: Selected template name
    
    Returns:
        Dictionary containing edited generation template and validation status
    """
    st.subheader("🎛️ Generation Template Editor")
    
    # Get current generation template content
    template_generator = data_gen.get_template_generator()
    current_template = template_generator.get_template_info(selected_template)
    
    if current_template:
        template_json = json.dumps(current_template, indent=2)
    else:
        # Create a default generation template structure if none exists
        default_template = {
            "StaticFields": {},
            "DynamicFields": {},
            "RandomFields": [],
            "LinkedFields": {}
        }
        template_json = json.dumps(default_template, indent=2)
        current_template = default_template
    
    # JSON editor
    with st.expander("Edit Generation Template", expanded=True):
        edited_template = st_ace(
            value=template_json,
            language="json",
            keybinding="sublime",
            height=500,
            key=f"generation_template_editor_{selected_template}",
            theme=st.session_state.ace_theme,
        )
        
        # Validate JSON and generation template structure
        template_valid = True
        parsed_template = {}
        try:
            parsed_template = json.loads(edited_template)
            
            # Validate generation template structure
            required_sections = ["StaticFields", "DynamicFields", "RandomFields", "LinkedFields"]
            validation_errors = []
            
            for section in required_sections:
                if section not in parsed_template:
                    validation_errors.append(f"Missing required section: {section}")
            
            # Validate RandomFields structure
            if "RandomFields" in parsed_template and isinstance(parsed_template["RandomFields"], list):
                for i, field in enumerate(parsed_template["RandomFields"]):
                    if not isinstance(field, dict) or "FieldName" not in field or "FieldType" not in field:
                        validation_errors.append(f"RandomFields[{i}] must have 'FieldName' and 'FieldType'")
            
            if validation_errors:
                st.error("❌ Generation template validation errors:")
                for error in validation_errors:
                    st.error(f"  • {error}")
                template_valid = False
                
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {e}")
            template_valid = False
    
    final_template = parsed_template if template_valid else current_template
    template_changed = template_valid and (json.dumps(parsed_template, sort_keys=True) != json.dumps(current_template, sort_keys=True))
    
    return {
        "template": final_template,
        "is_valid": template_valid,
        "template_changed": template_changed
    }


def _extract_field_paths(obj, prefix=""):
    """Extract all field paths from nested object using dot notation"""
    paths = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                paths.extend(_extract_field_paths(value, current_path))
            else:
                paths.append(current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{prefix}.{i}" if prefix else str(i)
            if isinstance(item, (dict, list)):
                paths.extend(_extract_field_paths(item, current_path))
            else:
                paths.append(current_path)
    
    return paths


def _get_nested_value(obj, path):
    """Get value from nested object using dot notation path"""
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    
    return current


def _save_template_changes(data_gen, template_name, new_template):
    """Save template changes to the DataGenerator"""
    try:
        data_gen.templates[template_name] = new_template
        return True
    except Exception as e:
        st.error(f"Error saving template: {e}")
        return False


def _reset_template(data_gen, template_name):
    """Reset template to original from file"""
    try:
        data_gen._load_templates()  # Reload from files
        return True
    except Exception as e:
        st.error(f"Error resetting template: {e}")
        return False


def _save_generation_template_changes(data_gen, template_name, new_template):
    """Save generation template changes to file"""
    import os
    try:
        # Get the template generator and save to the generation_templates directory
        template_generator = data_gen.get_template_generator()
        generation_templates_dir = template_generator.templates_dir
        
        # Ensure directory exists
        if not os.path.exists(generation_templates_dir):
            os.makedirs(generation_templates_dir)
        
        # Save to file
        file_path = os.path.join(generation_templates_dir, f"{template_name}.json")
        with open(file_path, 'w') as f:
            json.dump(new_template, f, indent=2)
        
        # Reload the generation templates to reflect changes
        template_generator.load_generation_templates()
        
        return True
    except Exception as e:
        st.error(f"Error saving generation template: {e}")
        return False


def _reset_generation_template(data_gen, template_name):
    """Reset generation template to original from file"""
    try:
        # Reload generation templates from files
        template_generator = data_gen.get_template_generator()
        template_generator.load_generation_templates()
        return True
    except Exception as e:
        st.error(f"Error resetting generation template: {e}")
        return False
