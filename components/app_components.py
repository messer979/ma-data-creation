"""
UI components and rendering functions for the Data Creation Tool
"""

import streamlit as st
from streamlit_ace import st_ace

import json
import os
import pandas as pd
from datetime import datetime
import time
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





def _update_main_template_from_table(selected_template: str, edited_df: pd.DataFrame):
    """Callback function to update main template when table changes"""
    try:
        main_key = f"main_template_{selected_template}"            
        
        # Reconstruct template from table data
        reconstructed_template = {
            "StaticFields": {},
            "SequenceFields": {},
            "RandomFields": {},
            "ArrayLengths": {},
            "LinkedFields": {},
            "QueryContextFields": {}
        }
        
        for _, row in edited_df.iterrows():
            field_name = str(row["Field Name"]).strip()
            field_type = str(row["Type"]).strip()
            field_value = str(row["Value"]).strip()
            
            # Skip empty rows
            if not field_name:
                continue
                
            try:
                if field_type == "StaticFields":
                    # Parse value appropriately
                    if field_value.lower() in ['true', 'false']:
                        reconstructed_template["StaticFields"][field_name] = field_value.lower() == 'true'
                    elif field_value.lower() == 'null':
                        reconstructed_template["StaticFields"][field_name] = None
                    elif field_value.isdigit():
                        reconstructed_template["StaticFields"][field_name] = int(field_value)
                    elif field_value.replace('.', '').isdigit():
                        reconstructed_template["StaticFields"][field_name] = float(field_value)
                    else:
                        reconstructed_template["StaticFields"][field_name] = field_value
                        
                elif field_type == "SequenceFields":
                    reconstructed_template["SequenceFields"][field_name] = field_value
                    
                elif field_type == "RandomFields":
                    reconstructed_template["RandomFields"][field_name] = field_value
                    
                elif field_type == "ArrayLengths":
                    try:
                        reconstructed_template["ArrayLengths"][field_name] = int(field_value)
                    except:
                        reconstructed_template["ArrayLengths"][field_name] = field_value
                        
                elif field_type == "LinkedFields":
                    targets = [t.strip() for t in field_value.split(",") if t.strip()]
                    reconstructed_template["LinkedFields"][field_name] = targets
                    
                elif field_type == "QueryContextFields":
                    query_spec = {}
                    pairs = field_value.split("|")
                    for pair in pairs:
                        if ":" in pair:
                            key, value = pair.split(":", 1)
                            query_spec[key.strip()] = value.strip()
                    reconstructed_template["QueryContextFields"][field_name] = query_spec
                    
            except Exception:
                continue
        
        # Remove empty sections
        reconstructed_template = {k: v for k, v in reconstructed_template.items() if v}
        
        # Update main template
        st.session_state[main_key] = reconstructed_template
        
        # Update template generator
        if 'data_gen' in st.session_state:
            template_generator = st.session_state.data_gen.get_template_generator()
            template_generator.generation_templates[selected_template] = reconstructed_template
        
    except Exception as e:
        st.error(f"Error updating template from table: {str(e)}")


def _update_main_template_from_editor(selected_template: str, editor_content:str):
    """Callback function to update main template when JSON editor changes"""
    try:
        main_key = f"main_template_{selected_template}"
        try:
            parsed_template = json.loads(editor_content)
            
            # Basic validation
            if isinstance(parsed_template, dict):
                # Update main template
                st.session_state[main_key] = parsed_template
                
                # Update template generator
                if 'data_gen' in st.session_state:
                    template_generator = st.session_state.data_gen.get_template_generator()
                    template_generator.generation_templates[selected_template] = parsed_template
                    
        except json.JSONDecodeError:
            # Invalid JSON, don't update
            pass
            
    except Exception as e:
        st.error(f"Error updating template from editor: {str(e)}")


def _sync_table_from_main(selected_template: str):
    """Sync table data from main template"""
    main_key = f"main_template_{selected_template}"
    table_key = f"table_template_{selected_template}"
    
    if main_key not in st.session_state:
        return
        
    main_template = st.session_state[main_key]
    
    # Convert main template to table rows
    rows = []
    
    # Process StaticFields
    for field_name, value in main_template.get("StaticFields", {}).items():
        rows.append({
            "Field Name": field_name,
            "Type": "StaticFields",
            "Value": str(value) if value is not None else ""
        })
    
    # Process SequenceFields
    for field_name, prefix in main_template.get("SequenceFields", {}).items():
        rows.append({
            "Field Name": field_name,
            "Type": "SequenceFields", 
            "Value": str(prefix)
        })
    
    # Process RandomFields
    for field_name, field_type in main_template.get("RandomFields", {}).items():
        rows.append({
            "Field Name": field_name,
            "Type": "RandomFields",
            "Value": str(field_type)
        })
    
    # Process ArrayLengths
    for array_name, length in main_template.get("ArrayLengths", {}).items():
        rows.append({
            "Field Name": array_name,
            "Type": "ArrayLengths",
            "Value": str(length)
        })
    
    # Process LinkedFields
    for source_field, target_fields in main_template.get("LinkedFields", {}).items():
        targets_str = ",".join(target_fields) if isinstance(target_fields, list) else str(target_fields)
        rows.append({
            "Field Name": source_field,
            "Type": "LinkedFields",
            "Value": targets_str
        })
    
    # Process QueryContextFields
    for field_name, query_spec in main_template.get("QueryContextFields", {}).items():
        if isinstance(query_spec, dict):
            value_parts = []
            for key, value in query_spec.items():
                value_parts.append(f"{key}:{value}")
            value_str = "|".join(value_parts)
        else:
            value_str = str(query_spec)
        
        rows.append({
            "Field Name": field_name,
            "Type": "QueryContextFields",
            "Value": value_str
        })
    
    # Create DataFrame and sort
    if rows:
        df = pd.DataFrame(rows)
        # Sort by type priority
        type_priority = {
            "SequenceFields": 0,
            "StaticFields": 1,
            "RandomFields": 2,
            "ArrayLengths": 3,
            "LinkedFields": 4,
            "QueryContextFields": 5
        }
        df['_sort_priority'] = df['Type'].map(type_priority)
        df = df.sort_values(['_sort_priority', 'Field Name']).drop('_sort_priority', axis=1).reset_index(drop=True)
    else:
        df = pd.DataFrame(columns=["Field Name", "Type", "Value"])
    
    # st.session_state[table_key] = df
    return df


def _sync_editor_from_main(selected_template: str):
    """Sync editor content from main template"""
    main_key = f"main_template_{selected_template}"
    editor_key = f"editor_template_{selected_template}"
    
    if main_key not in st.session_state:
        return
        
    main_template = st.session_state[main_key]
    editor_content = json.dumps(main_template, indent=2)
    st.session_state[editor_key] = editor_content


def render_tabular_template_editor(data_gen, selected_template: str) -> Dict[str, Any]:
    """
    Render tabular template editor for generation templates
    
    Args:
        data_gen: DataGenerator instance
        selected_template: Selected template name
    
    Returns:
        Dictionary containing edited generation template and validation status
    """
    st.subheader("📊 Template Editor")
    if st.session_state['editor_active'] == True:
        
        st.session_state['editor_active'] = False
    current_df = _sync_table_from_main(selected_template)
    # Initialize main template from current template if it doesn't exist
    main_key = f"main_template_{selected_template}"
    table_key = f"table_template_{selected_template}"
    
    if main_key not in st.session_state:
        # Get current generation template content
        template_generator = data_gen.get_template_generator()
        current_template = template_generator.get_template_info(selected_template)
        
        if not current_template:
            current_template = {
                "StaticFields": {},
                "SequenceFields": {},
                "RandomFields": {},
                "LinkedFields": {},
                "ArrayLengths": {}
            }
        
        st.session_state[main_key] = current_template
    
    

    # Define type options for dropdown with priority order
    type_options = [
        "SequenceFields",
        "StaticFields", 
        "RandomFields",
        "ArrayLengths",
        "LinkedFields",
        "QueryContextFields"
    ]
    
    # Create priority mapping for sorting
    type_priority = {type_name: i for i, type_name in enumerate(type_options)}
    
    # Create the editable data editor
    with st.expander("Edit Template Fields", expanded=True):            
        
        # Use st.data_editor for tabular editing with on_change callback
        edited_df = st.data_editor(
            current_df,
            column_config={
                "Field Name": st.column_config.TextColumn(
                    "Field Name",
                    help="The field path (e.g., 'PurchaseOrderStatus' or 'PurchaseOrderLine.ItemId')",
                    width="medium"
                ),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    help="The type of field configuration",
                    options=type_options,
                    width="small"
                ),
                "Value": st.column_config.TextColumn(
                    "Value",
                    help="The value or specification for this field",
                    width="large"
                )
            },
            use_container_width=True,
            hide_index=True,
            key=table_key,
            num_rows="dynamic",
        )
        
        # Add button to update main template from table changes
        if st.button("📤 Update Template", 
                    help="Apply table changes to the main template", 
                    use_container_width=True,
                    type="primary"):
            _update_main_template_from_table(selected_template, edited_df)
            st.success("✅ Template updated successfully!")
            st.rerun()
    # _update_main_template_from_table(selected_template, edited_df)
    # # Get current main template for return
    current_main_template = st.session_state.get(main_key, {})
    
    
    return {
        "template": current_main_template,
        "is_valid": True,
        "template_changed": True
    }


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
    
    # Initialize main template from current template if it doesn't exist
    main_key = f"main_template_{selected_template}"
    editor_key = f"editor_template_{selected_template}"

    if main_key not in st.session_state:
        # Get current generation template content
        template_generator = data_gen.get_template_generator()
        current_template = template_generator.get_template_info(selected_template)
        
        if not current_template:
            current_template = {
                "StaticFields": {},
                "SequenceFields": {},
                "RandomFields": {},
                "LinkedFields": {},
                "ArrayLengths": {}
            }
        
        st.session_state[main_key] = current_template

    if st.session_state['editor_active'] == False or editor_key not in st.session_state:
        _sync_editor_from_main(selected_template)
        st.session_state['editor_active'] = True

    # JSON editor
    with st.expander("Edit Generation Template", expanded=True):
        # Use st_ace for JSON editing with callback
        edited_template = st_ace(
            value=st.session_state[editor_key],
            language="json",
            keybinding="sublime",
            height=500,
            key=editor_key,
            theme=st.session_state.get("ace_theme", "github"),
            # on_change=lambda: _update_main_template_from_editor(selected_template)
        )
        time.sleep(1)  # Allow time for editor to update session state
        _update_main_template_from_editor(selected_template, st.session_state[editor_key])

        # Validate current editor content
        current_editor_content = st.session_state.get(editor_key, "{}")
        template_valid = True
        parsed_template = {}
        
        try:
            parsed_template = json.loads(current_editor_content)
            st.success("✅ Valid JSON syntax")
            
            # Check generation template structure
            expected_keys = ["StaticFields", "SequenceFields", "RandomFields", "LinkedFields", "ArrayLengths"]
                            
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON syntax error: {str(e)}")
            template_valid = False
            parsed_template = st.session_state.get(main_key, {})
        except Exception as e:
            st.error(f"❌ Template validation error: {str(e)}")
            template_valid = False
            parsed_template = st.session_state.get(main_key, {})
    
    # Get current main template for return
    current_main_template = st.session_state.get(main_key, {})
    
    return {
        "template": current_main_template,
        "is_valid": template_valid,
        "template_changed": True
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




def render_editor(selected_template):
    editor_mode = st.radio(
        "Template Editor Mode",
        ["JSON Editor", "Tabular Editor"],
        horizontal=True,
        help="Choose between tabular editing or direct JSON editing",
        key="editor_radio"
    )
    if 'editor_active' not in st.session_state:
        st.session_state['editor_active'] = False
    # _sync_table_from_main(selected_template)
    # _sync_editor_from_main(selected_template)

    if editor_mode == "Tabular Editor":
        template_editor_result = render_tabular_template_editor(
            st.session_state.data_gen,
            selected_template
        )
    else:
        template_editor_result = render_template_editor(
            st.session_state.data_gen,
            selected_template
        )
    main_key = f"main_template_{selected_template}"
    return template_editor_result
    # st.write(st.session_state['editor_active'])
    # st.code(json.dumps(st.session_state[main_key], indent=2))

