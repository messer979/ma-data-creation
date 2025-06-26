"""
Session-Only Template Manager
Handles import/export and management of templates in session memory only
No templates are stored on the server - everything is session-based
"""

import json
import os
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import glob

from components.sidebar import render_sidebar
from templates.session_base_template_manager import SessionBaseTemplateManager
from templates.bulk_template_manager import BulkTemplateManager
from data_creation.template_generator import TemplateGenerator

# Initialize the session-only template manager
def get_session_template_manager():
    """Get session-only template manager instance - no server storage"""
    return SessionBaseTemplateManager()



# Get template manager instance
template_manager = get_session_template_manager()
template_generator = TemplateGenerator()

# Main UI
st.set_page_config(
    page_title="RAD: Template Management", 
    page_icon="🚀", 
    layout="wide"
)
st.title("🗂️ Template Management")

# Sidebar navigation
render_sidebar()
# Template overview expanders
with st.sidebar:
    with st.expander(f"📋 Base Templates ({len(template_manager.base_templates)})", expanded=False):
        if template_manager.base_templates:
            for template_name in sorted(template_manager.base_templates.keys()):
                template_info = template_manager.get_template_info(template_name)
                field_count = template_info.get('field_count', 0)
                st.write(f"• **{template_name}** ({field_count} fields)")
        else:
            st.info("No base templates loaded in session")

    with st.expander(f"⚙️ Generation Templates ({len(template_generator.generation_templates)})", expanded=False):
        if template_generator.generation_templates:
            for template_name in sorted(template_generator.generation_templates.keys()):
                template = template_generator.generation_templates[template_name]
                field_count = 0
                if isinstance(template, dict):
                    field_count += len(template.get("StaticFields", {}))
                    field_count += len(template.get("DynamicFields", {}))
                    field_count += len(template.get("RandomFields", []))
                    field_count += len(template.get("LinkedFields", {}))
                st.write(f"• **{template_name}** ({field_count} total fields)")
        else:
            st.info("No generation templates loaded in session")


# Warning about session-only storage

st.markdown("""
Manage templates that define the structure for data generation.
These templates contain the default field values and structure for different API endpoints.
**All templates exist only in your current session - no server storage.**
""")


# Session management buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Refresh Session", help="Reinitialize session templates"):
        template_manager.load_templates()
        st.rerun()

with col2:
    if st.button("🗑️ Clear All Templates", help="Remove all templates from session", type="secondary"):
        if st.session_state.get("confirm_clear_all", False):
            template_manager.clear_all_templates()
            template_generator.generation_templates.clear()
            st.success("All templates cleared from session")
            st.rerun()
        else:
            st.session_state["confirm_clear_all"] = True
            st.warning("Click again to confirm clearing all templates")

with col3:
    st.metric("Base Templates", len(template_manager.base_templates))

st.markdown("---")


# Main functionality tabs
tab1, tab2, tab3 = st.tabs(["📤 Export/Import", "📝 Template Editor", "📊 Template Overview"])

with tab1:
    st.header("📤 Export & Import Templates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Export All Base Templates")
        st.write(f"Export all {len(template_manager.base_templates)} base templates as a single JSON file.")
        
        if template_manager.base_templates:
            json_str, export_data = template_manager.export_all_templates()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_base_templates_export_{timestamp}.json"
            
            st.download_button(
                label="📥 Download Base Templates Export",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
                help=f"Download all {len(template_manager.base_templates)} base templates from session"
            )
            
            # Show export preview
            with st.expander("🔍 Export Preview", expanded=False):
                st.json(export_data["metadata"])
                st.write("**Templates to export:**")
                for template in export_data["templates"]:
                    st.write(f"• {template['name']}")
        else:
            st.info("No templates in session to export")
    
    with col2:
        st.subheader("📥 Import Base Templates")
        st.write("Import base templates from a JSON file into your session.")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose base templates JSON file", 
            type=['json'],
            help="Upload a JSON file containing base templates (will be stored in session only)",
            key="base_template_uploader"
        )
        
        if uploaded_file is not None:
            try:
                # Read the uploaded file
                content = uploaded_file.read().decode('utf-8')
                
                # Preview the import
                try:
                    parsed_preview = json.loads(content)
                    if "templates" in parsed_preview and isinstance(parsed_preview["templates"], list):
                        st.info(f"📋 Ready to import {len(parsed_preview['templates'])} templates")
                        
                        # Show template names and conflicts
                        with st.expander("🔍 Preview Templates", expanded=True):
                            for template in parsed_preview["templates"]:
                                if isinstance(template, dict) and "name" in template:
                                    exists = template["name"] in template_manager.base_templates
                                    status = "⚠️ Will overwrite" if exists else "✅ New"
                                    st.write(f"• **{template['name']}** {status}")
                    else:
                        st.error("Invalid template format - missing 'templates' array")
                        st.stop()
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
                    st.stop()
                
                # Import options
                overwrite_existing = st.checkbox("Overwrite existing templates", value=True)
                
                # Import button
                if st.button("🔼 Import Templates", use_container_width=True, type="primary"):
                    with st.spinner("Importing templates..."):
                        success, message, imported, skipped = template_manager.import_templates(
                            content, overwrite_existing
                        )
                    
                    if success:
                        st.success(f"✅ {message}")
                        
                        if imported:
                            st.write("**Imported templates:**")
                            for template_name in imported:
                                st.write(f"• {template_name}")
                        
                        if skipped:
                            st.write("**Skipped templates:**")
                            for template_name in skipped:
                                st.write(f"• {template_name}")
                          # Refresh the session to show updated templates
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                        
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

with tab2:
    st.header("📝 Template Editor")
    
    if template_manager.base_templates:
        # Template selector
        selected_template = st.selectbox(
            "Select template to edit:",
            options=list(template_manager.base_templates.keys()),
            help="Choose a template to view or edit (session only)"
        )
        
        if selected_template:
            st.subheader(f"Editing: {selected_template}")
            
            # Template actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📥 Download Template", use_container_width=True):
                    template_json = json.dumps(template_manager.base_templates[selected_template], indent=2)
                    st.download_button(
                        label="💾 Save JSON File",
                        data=template_json,
                        file_name=f"{selected_template}.json",
                        mime="application/json"
                    )
            
            with col2:
                if st.button("🗑️ Delete Template", use_container_width=True, type="secondary"):
                    if st.session_state.get(f"confirm_delete_{selected_template}", False):
                        if template_manager.delete_template(selected_template):
                            st.success(f"Template '{selected_template}' deleted from session")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete template '{selected_template}'")
                    else:
                        st.session_state[f"confirm_delete_{selected_template}"] = True
                        st.warning("Click again to confirm deletion")
            
            with col3:
                if st.button("🔄 Refresh", use_container_width=True):
                    template_manager.load_templates()
                    st.rerun()
            
            # Template content viewer/editor
            st.markdown("### Template Content")
            
            # Show template info
            template_info = template_manager.get_template_info(selected_template)
            
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("Size", f"{template_info.get('size_bytes', 0)} bytes")
            with info_col2:
                st.metric("Fields", template_info.get('field_count', 0))
            with info_col3:
                st.metric("Type", template_info.get('structure_type', 'Unknown'))
            
            # JSON editor
            template_content = template_manager.base_templates[selected_template]
            
            # Use text area for editing
            json_str = json.dumps(template_content, indent=2)
            edited_json = st.text_area(
                "Template JSON:",
                value=json_str,
                height=400,
                help="Edit the template JSON structure"
            )
            
            # Save changes button
            if st.button("💾 Save Changes", type="primary"):
                try:
                    # Parse and validate the edited JSON
                    new_template_content = json.loads(edited_json)
                      # Save the template to session
                    if template_manager.save_template(selected_template, new_template_content):
                        st.success(f"Template '{selected_template}' saved to session")
                        st.rerun()
                    else:
                        st.error("Failed to save template to session")
                        
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"Error saving template: {str(e)}")
    
    else:
        st.info("No templates in session. Import some templates to get started.")
    
    # Add new template section
    st.markdown("---")
    st.subheader("➕ Create New Template in Session")
    
    with st.expander("Create New Template", expanded=False):
        new_template_name = st.text_input("Template Name:", help="Enter name for the new template (will be stored in session only)")
        
        new_template_content = st.text_area(
            "Template JSON Content:",
            value='{\n  "example_field": "example_value"\n}',
            height=200,
            help="Enter the JSON content for the new template (session only)"
        )
        
        if st.button("✨ Create Template", type="primary"):
            if new_template_name and new_template_content:
                try:
                    # Validate JSON
                    parsed_content = json.loads(new_template_content)
                    
                    # Check if template already exists in session
                    if new_template_name in template_manager.base_templates:
                        st.error(f"Template '{new_template_name}' already exists in session")
                    else:
                        # Create the template in session
                        if template_manager.save_template(new_template_name, parsed_content):
                            st.success(f"Template '{new_template_name}' created in session")
                            st.rerun()
                        else:
                            st.error("Failed to create template in session")
                            
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"Error creating template: {str(e)}")
            else:
                st.error("Please provide both template name and content")

with tab3:
    st.header("📊 Template Overview")
    
    if template_manager.base_templates:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Templates", len(template_manager.base_templates))
        
        with col2:
            total_size = sum(len(json.dumps(template)) for template in template_manager.base_templates.values())
            st.metric("Total Size", f"{total_size:,} bytes")
        
        with col3:
            total_fields = 0
            for template in template_manager.base_templates.values():
                if isinstance(template, dict):
                    total_fields += len(template)
            st.metric("Total Fields", total_fields)
        
        with col4:
            st.metric("Session Storage", "Memory Only")
        
        st.markdown("---")
        
        # Template details table
        st.subheader("📋 Template Details")
        
        # Create a table of template information
        template_data = []
        for template_name in sorted(template_manager.base_templates.keys()):
            info = template_manager.get_template_info(template_name)
            template_data.append({
                "Name": template_name,
                "Type": info.get("structure_type", "Unknown"),
                "Fields/Items": info.get("field_count", 0),
                "Size (bytes)": info.get("size_bytes", 0)
            })
        
        if template_data:
            st.dataframe(template_data, use_container_width=True)
        
        # Detailed view
        st.markdown("### 🔍 Detailed Template Information")
        
        for template_name in sorted(template_manager.base_templates.keys()):
            with st.expander(f"📄 {template_name}", expanded=False):
                info = template_manager.get_template_info(template_name)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Type:** {info.get('structure_type', 'Unknown')}")
                    st.write(f"**Size:** {info.get('size_bytes', 0):,} bytes")
                    st.write(f"**Fields/Items:** {info.get('field_count', 0)}")
                
                with col2:
                    if "fields" in info and info["fields"]:
                        st.write("**Sample Fields:**")
                        for field in info["fields"]:
                            st.write(f"• {field}")
                        if len(info.get("fields", [])) < info.get("field_count", 0):
                            st.write(f"... and {info.get('field_count', 0) - len(info.get('fields', []))} more")
                
                # JSON preview (collapsed)
                st.json(template_manager.base_templates[template_name])
    
    else:
        st.info("No templates loaded in session. Import or create templates to see overview.")

# Sidebar help
with st.sidebar:
    st.markdown("### 💡 Help & Tips")
    
    with st.expander("🗂️ About Session Templates"):
        st.markdown("""
        **Session templates** define the structure and default values for API requests.
        
        ⚠️ **Important**: Templates are stored in your browser session only:
        - No server-side storage
        - Lost when page is refreshed or browser closed
        - Export templates to save them permanently
        """)
    
    with st.expander("📤 Export/Import"):
        st.markdown("""
        **Export:** Download all templates as a single JSON file
        
        **Import:** Upload a JSON file with multiple templates (session only)
        
        The format includes metadata and template array structure.
        """)
    
    with st.expander("⚠️ Important Notes"):
        st.markdown("""
        - Templates are lost on page refresh
        - Make sure to export to save your work. 
        - No server-side persistence or storage
        - Session-based storage ensures server remains stateless
        """)

st.markdown("---")

st.markdown("### 📦 Generation Template Management")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📤 Export All Generation Templates")
    st.write(f"Export all {len(template_generator.generation_templates)} generation templates as a single JSON file.")
    json_str, export_data = BulkTemplateManager.export_all_templates(template_generator)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_generation_templates_export_{timestamp}.json"

    st.download_button(
        label="📥 Download Generation Templates Export",
        data=json_str,
        file_name=filename,
        mime="application/json",
        use_container_width=True,
        help=f"Download all {len(template_generator.generation_templates)} generation templates from session"
    )


with col2:
    st.markdown("### 📤 Import Generation Templates")
    st.write("Import generation templates from a JSON file into your session.")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose generation templates JSON file", 
        type=['json'],
        help="Upload a JSON file containing generation templates"
    )
    if 'last_gen_file' not in st.session_state:
        st.session_state.last_gen_file = None
    
    if uploaded_file is not None:
        if st.session_state.last_gen_file == uploaded_file.file_id:
            st.success("File successfully imported!")
            
        try:
            # Read the uploaded file
            content = uploaded_file.read().decode('utf-8')
            
            # Preview the import
            try:
                parsed_preview = json.loads(content)
                if "templates" in parsed_preview and isinstance(parsed_preview["templates"], list):
                    st.info(f"📋 Ready to import {len(parsed_preview['templates'])} templates")
                    
                    # Show template names
                    with st.expander("🔍 Preview Templates", expanded=False):
                        for template in parsed_preview["templates"]:
                            if isinstance(template, dict) and "name" in template:
                                exists = template["name"] in template_generator.generation_templates
                                status = "⚠️ Exists" if exists else "✅ New"
                                st.write(f"• {template['name']} {status}")
                else:
                    st.error("Invalid template format")
                    st.stop()
            except json.JSONDecodeError:
                st.error("Invalid JSON format")
                st.stop()
            
            # Import button
            if st.button("🔼 Import Templates", use_container_width=True):
                success, message, imported, skipped = BulkTemplateManager.import_all_templates(
                    template_generator, content
                )
                
                if success:
                    st.session_state.last_gen_file = uploaded_file.file_id
                    
                    if imported:
                        st.rerun()
                else:
                    st.error(f"❌ {message}")
                    
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

st.markdown("---")
st.markdown("### 📊 Generation Templates")

if template_generator.generation_templates:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Templates", len(template_generator.generation_templates))
    
    with col2:
        # Calculate total fields across all templates
        total_fields = 0
        for template in template_generator.generation_templates.values():
            if isinstance(template, dict):
                total_fields += len(template.get("StaticFields", {}))
                total_fields += len(template.get("DynamicFields", {}))
                total_fields += len(template.get("RandomFields", []))
                total_fields += len(template.get("LinkedFields", {}))
        st.metric("Total Fields", total_fields)
    
    with col3:
        # Show session status
        st.metric("Storage", "Session Only")
    
    # List all templates
    with st.expander("📝 Template List", expanded=False):
        for template_name in sorted(template_generator.generation_templates.keys()):
            template = template_generator.generation_templates[template_name]
            field_count = 0
            if isinstance(template, dict):
                field_count += len(template.get("StaticFields", {}))
                field_count += len(template.get("DynamicFields", {}))
                field_count += len(template.get("RandomFields", []))
                field_count += len(template.get("LinkedFields", {}))
            
            st.write(f"• **{template_name}** ({field_count} fields)")
else:
    st.info("No generation templates currently loaded in session.")
