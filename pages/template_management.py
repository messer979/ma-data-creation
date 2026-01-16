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

from components.sidebar import render_sidebar, mark_config_updated
from templates.session_base_template_manager import SessionBaseTemplateManager
from templates.bulk_template_manager import BulkTemplateManager
from data_creation.template_generator import TemplateGenerator
from data_creation.dev_config import is_dev_mode, get_dev_templates


def _sync_generator_to_session_templates(template_generator):
    """
    Sync templates from the template generator to session state
    This ensures imported templates are available in the editor
    
    Args:
        template_generator: TemplateGenerator instance with templates to sync
    """
    for template_name, template_content in template_generator.generation_templates.items():
        # Create session state key for this template
        content_key = f"template_content_{template_name}"
        
        # Convert template content to JSON string and store in session state
        try:
            template_json = json.dumps(template_content, indent=2)
            st.session_state[content_key] = template_json
        except Exception as e:
            continue



def _sync_session_templates_to_generator(template_generator):
    """
    Sync all template changes from session state to the template generator
    This ensures exports include the latest edits from the UI
    
    Args:
        template_generator: TemplateGenerator instance to update
    """
    # Find all template content keys in session state
    template_content_keys = [k for k in st.session_state.keys() if k.startswith('template_content_')]
    
    for content_key in template_content_keys:
        # Extract template name from the key
        template_name = content_key.replace('template_content_', '')
        
        try:
            # Get the template content from session state
            template_json = st.session_state[content_key]
            
            # Parse and validate the JSON
            template_content = json.loads(template_json)
            
            # Update the template generator with the session state content
            template_generator.generation_templates[template_name] = template_content
            
        except (json.JSONDecodeError, KeyError) as e:
            # Skip invalid templates but don't break the export
            st.error(f"Warning: Could not sync template {template_name}: {e}")
            continue


# Initialize the session-only template manager
def get_session_template_manager():
    """Get session-only template manager instance - no server storage"""
    return SessionBaseTemplateManager()


def load_dev_templates_if_dev_mode():
    """
    Load templates from dev_gen_templates.json if in dev mode
    These will be merged with the session-based templates
    """
    if not is_dev_mode():
        return
    
    # Only load once per session to avoid overriding user changes
    if st.session_state.get('dev_templates_loaded_to_manager', False):
        return
    
    dev_templates = get_dev_templates()
    if not dev_templates:
        return
    
    try:
               
        # Also add templates to the generation templates session state
        for template_name, template_content in dev_templates.items():
            # Create session state key for generation templates
            if 'session_generation_templates' not in st.session_state:
                st.session_state['session_generation_templates'] = {}
            
            # Add template to generation templates
            st.session_state['session_generation_templates'][template_name] = template_content
            
            # Create content key for editor
            content_key = f"template_content_{template_name}"
            
            # Convert template content to JSON string for editor
            try:
                template_json = json.dumps(template_content, indent=2)
                st.session_state[content_key] = template_json
            except Exception as e:
                continue
            
        # Mark as loaded to prevent re-loading
        st.session_state['dev_templates_loaded_to_manager'] = True
        
        # Show a subtle notification
        if dev_templates:
            st.sidebar.info(f"🔧 Dev mode: Loaded {len(dev_templates)} templates from JSON file")
            
    except Exception as e:
        st.sidebar.error(f"Error loading dev templates: {e}")

# Main UI
st.set_page_config(
    page_title="RAD: Template Management", 
    page_icon="🚀", 
    layout="wide"
)
st.title("🗂️ Template Management")

# Get template manager instance
template_manager = get_session_template_manager()
template_generator = TemplateGenerator()

# Load templates from dev config if in dev mode
load_dev_templates_if_dev_mode()


# Sidebar navigation
render_sidebar()
# Template overview expanders


# Warning about session-only storage

st.markdown("""
Manage templates that define the structure for data generation.
These templates contain the default field values and structure for different API endpoints.
**All templates exist only in your current session - no server storage.**
""")


# Main functionality tabs
tab1, tab2, tab3 = st.tabs(["📤 Bulk Export/Import", "📝 Template Editor", "📊 Template Overview"])

with tab1:
    st.header("📤 Bulk Export & Import All Templates")
    st.markdown("Export or import **all base and generation templates** in a single operation.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Export All Templates")
        st.write("Export **all base and generation templates** as a single comprehensive JSON file.")
        
        # Sync any session state changes to template generator before export
        _sync_session_templates_to_generator(template_generator)
        
        # Prepare combined export data
        combined_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_tool": "RAD Template Management - Bulk Export",
                "base_template_count": len(template_manager.base_templates),
                "generation_template_count": len(template_generator.generation_templates),
                "total_template_count": len(template_manager.base_templates) + len(template_generator.generation_templates)
            },
            "base_templates": [],
            "generation_templates": []
        }
        
        # Add base templates
        for template_name, template_content in template_manager.base_templates.items():
            combined_export["base_templates"].append({
                "name": template_name,
                "content": template_content
            })
        
        # Add generation templates
        for template_name, template_content in template_generator.generation_templates.items():
            combined_export["generation_templates"].append({
                "name": template_name,
                "content": template_content
            })
        
        # Convert to JSON string
        json_str = json.dumps(combined_export, indent=2)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"all_templates_export_{timestamp}.json"
        
        if template_manager.base_templates or template_generator.generation_templates:
            st.download_button(
                label=f"📥 Download All Templates ({combined_export['metadata']['total_template_count']} total)",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
                type="primary",
                help=f"Download {combined_export['metadata']['base_template_count']} base + {combined_export['metadata']['generation_template_count']} generation templates"
            )
            
            # Show export preview
            with st.expander("🔍 Export Preview", expanded=False):
                st.json(combined_export["metadata"])
                st.write(f"**Base Templates ({len(combined_export['base_templates'])}):**")
                for template in combined_export["base_templates"]:
                    st.write(f"• {template['name']}")
                st.write(f"**Generation Templates ({len(combined_export['generation_templates'])}):**")
                for template in combined_export["generation_templates"]:
                    st.write(f"• {template['name']}")
        else:
            st.info("No templates in session to export")
    
    with col2:
        st.subheader("📥 Import All Templates")
        st.write("Import **base and generation templates** from a comprehensive JSON file.")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose templates JSON file", 
            type=['json'],
            help="Upload a JSON file containing both base and generation templates",
            key="bulk_template_uploader"
        )
        
        if uploaded_file is not None:
            try:
                # Read the uploaded file
                content = uploaded_file.read().decode('utf-8')
                parsed_data = json.loads(content)
                
                # Validate structure
                has_base = "base_templates" in parsed_data and isinstance(parsed_data["base_templates"], list)
                has_gen = "generation_templates" in parsed_data and isinstance(parsed_data["generation_templates"], list)
                
                if not (has_base or has_gen):
                    st.error("Invalid format: Must contain 'base_templates' and/or 'generation_templates' arrays")
                    st.stop()
                
                base_count = len(parsed_data.get("base_templates", []))
                gen_count = len(parsed_data.get("generation_templates", []))
                total_count = base_count + gen_count
                
                st.info(f"📋 Ready to import {total_count} templates ({base_count} base + {gen_count} generation)")
                
                # Show template preview with conflict detection
                with st.expander("🔍 Preview Templates", expanded=True):
                    if has_base and base_count > 0:
                        st.write("**Base Templates:**")
                        for template in parsed_data["base_templates"]:
                            if isinstance(template, dict) and "name" in template:
                                exists = template["name"] in template_manager.base_templates
                                status = "⚠️ Will overwrite" if exists else "✅ New"
                                st.write(f"• **{template['name']}** {status}")
                    
                    if has_gen and gen_count > 0:
                        st.write("**Generation Templates:**")
                        for template in parsed_data["generation_templates"]:
                            if isinstance(template, dict) and "name" in template:
                                exists = template["name"] in template_generator.generation_templates
                                status = "⚠️ Will overwrite" if exists else "✅ New"
                                st.write(f"• **{template['name']}** {status}")
                
                # Import options
                overwrite_existing = st.checkbox("Overwrite existing templates", value=True, 
                                                help="If checked, existing templates will be replaced")
                
                # Import button
                if st.button("🔼 Import All Templates", use_container_width=True, type="primary"):
                    with st.spinner("Importing templates..."):
                        imported_base = []
                        skipped_base = []
                        imported_gen = []
                        skipped_gen = []
                        errors = []
                        
                        # Import base templates
                        if has_base:
                            for template_data in parsed_data["base_templates"]:
                                try:
                                    if not isinstance(template_data, dict) or "name" not in template_data or "content" not in template_data:
                                        continue
                                    
                                    template_name = template_data["name"]
                                    template_content = template_data["content"]
                                    
                                    # Check if exists and overwrite setting
                                    if template_name in template_manager.base_templates and not overwrite_existing:
                                        skipped_base.append(template_name)
                                        continue
                                    
                                    # Save template
                                    if template_manager.save_template(template_name, template_content):
                                        imported_base.append(template_name)
                                    else:
                                        errors.append(f"Failed to save base template: {template_name}")
                                except Exception as e:
                                    errors.append(f"Error importing base template: {str(e)}")
                        
                        # Import generation templates
                        if has_gen:
                            for template_data in parsed_data["generation_templates"]:
                                try:
                                    if not isinstance(template_data, dict) or "name" not in template_data or "content" not in template_data:
                                        continue
                                    
                                    template_name = template_data["name"]
                                    template_content = template_data["content"]
                                    
                                    # Check if exists and overwrite setting
                                    if template_name in template_generator.generation_templates and not overwrite_existing:
                                        skipped_gen.append(template_name)
                                        continue
                                    
                                    # Save template to generator
                                    template_generator.generation_templates[template_name] = template_content
                                    
                                    # Sync to session state for editor
                                    content_key = f"template_content_{template_name}"
                                    st.session_state[content_key] = json.dumps(template_content, indent=2)
                                    
                                    imported_gen.append(template_name)
                                except Exception as e:
                                    errors.append(f"Error importing generation template: {str(e)}")
                    
                    # Show results
                    total_imported = len(imported_base) + len(imported_gen)
                    total_skipped = len(skipped_base) + len(skipped_gen)
                    
                    if total_imported > 0:
                        mark_config_updated()
                        st.success(f"✅ Successfully imported {total_imported} templates ({len(imported_base)} base + {len(imported_gen)} generation)")
                        
                        if imported_base:
                            with st.expander("Imported Base Templates"):
                                for name in imported_base:
                                    st.write(f"• {name}")
                        
                        if imported_gen:
                            with st.expander("Imported Generation Templates"):
                                for name in imported_gen:
                                    st.write(f"• {name}")
                    
                    if total_skipped > 0:
                        st.warning(f"⚠️ Skipped {total_skipped} existing templates ({len(skipped_base)} base + {len(skipped_gen)} generation)")
                        
                        if skipped_base:
                            with st.expander("Skipped Base Templates"):
                                for name in skipped_base:
                                    st.write(f"• {name}")
                        
                        if skipped_gen:
                            with st.expander("Skipped Generation Templates"):
                                for name in skipped_gen:
                                    st.write(f"• {name}")
                    
                    if errors:
                        st.error(f"❌ {len(errors)} errors occurred during import")
                        with st.expander("View Errors"):
                            for error in errors:
                                st.write(f"• {error}")
                    
                    if total_imported > 0:
                        st.rerun()
                        
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {str(e)}")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

with tab2:
    st.header("📝 Base Template Editor")
    
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
                            mark_config_updated()
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
                        mark_config_updated()
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
                            mark_config_updated()
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

st.markdown("### 📊 Template Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Base Templates", len(template_manager.base_templates))

with col2:
    st.metric("Generation Templates", len(template_generator.generation_templates))

with col3:
    total_templates = len(template_manager.base_templates) + len(template_generator.generation_templates)
    st.metric("Total Templates", total_templates)

with col4:
    st.metric("Storage", "Session Only")

# Quick template lists
col1, col2 = st.columns(2)

with col1:
    if template_manager.base_templates:
        with st.expander("📄 Base Templates List", expanded=False):
            for template_name in sorted(template_manager.base_templates.keys()):
                info = template_manager.get_template_info(template_name)
                st.write(f"• **{template_name}** ({info.get('field_count', 0)} fields)")
    else:
        st.info("No base templates loaded")

with col2:
    if template_generator.generation_templates:
        with st.expander("📝 Generation Templates List", expanded=False):
            for template_name in sorted(template_generator.generation_templates.keys()):
                template = template_generator.generation_templates[template_name]
                field_count = 0
                if isinstance(template, dict):
                    field_count += len(template.get("StaticFields", {}))
                    field_count += len(template.get("SequenceFields", {}))
                    field_count += len(template.get("RandomFields", {}))
                    field_count += len(template.get("LinkedFields", {}))
                st.write(f"• **{template_name}** ({field_count} fields)")
    else:
        st.info("No generation templates loaded")

