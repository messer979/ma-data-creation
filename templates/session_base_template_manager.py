"""
Session-Only Base Template Manager
Handles base API templates in session memory only - no server-side storage
Loads read-only examples from disk on startup, but all modifications are session-only
"""

import json
import os
import glob
import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Tuple


class SessionBaseTemplateManager:
    """Manages base API templates in session memory only - loads read-only examples on startup"""
    
    def __init__(self, templates_dir: str = "templates/base_templates"):
        self.templates_dir = templates_dir
        self.session_key = "session_base_templates"
        self.examples_loaded_key = "session_base_examples_loaded"
        self._ensure_session_initialized()
    
    def _ensure_session_initialized(self):
        """Ensure session state is initialized and load examples if needed"""
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {}
        
        # Load read-only examples on first initialization
        if not st.session_state.get(self.examples_loaded_key, False):
            self._load_examples_to_session()
            st.session_state[self.examples_loaded_key] = True
    
    def _load_examples_to_session(self):
        """Load example templates from disk into session as starting examples"""
        if not os.path.exists(self.templates_dir):
            return
        
        # Load all JSON files from templates directory as read-only examples
        template_files = glob.glob(os.path.join(self.templates_dir, "*.json"))
        
        for file_path in template_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    template_data = json.loads(content)
                    
                # Use filename (without extension) as template name
                template_name = os.path.splitext(os.path.basename(file_path))[0]
                st.session_state[self.session_key][template_name] = template_data
                
            except Exception as e:
                # Silently skip problematic files - this is just for examples
                continue
    
    @property
    def base_templates(self) -> Dict[str, Any]:
        """Get base templates from session state"""
        self._ensure_session_initialized()
        return st.session_state[self.session_key]
    
    def load_templates(self):
        """Reload examples from disk into session (useful for refresh)"""
        self._load_examples_to_session()
    
    def clear_all_templates(self):
        """Clear all templates from session"""
        self._ensure_session_initialized()
        st.session_state[self.session_key] = {}
    
    def save_template(self, template_name: str, template_content: Any) -> bool:
        """Save template to session memory only"""
        try:
            self._ensure_session_initialized()
            st.session_state[self.session_key][template_name] = template_content
            return True
        except Exception as e:
            st.error(f"Error saving template {template_name} to session: {str(e)}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """Delete template from session memory"""
        try:
            self._ensure_session_initialized()
            if template_name in st.session_state[self.session_key]:
                del st.session_state[self.session_key][template_name]
            return True
        except Exception as e:
            st.error(f"Error deleting template {template_name}: {str(e)}")
            return False
    
    def export_all_templates(self) -> Tuple[str, Dict[str, Any]]:
        """Export all base templates as a single JSON structure"""
        templates_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_tool": "Data Creation Tool - Session Base Template Manager",
                "template_count": len(self.base_templates),
                "export_type": "base_templates",
                "storage_type": "session_only"
            },
            "templates": []
        }
        
        # Convert templates to array format with metadata
        for template_name, template_content in self.base_templates.items():
            template_entry = {
                "name": template_name,
                "content": template_content,
                "file_name": f"{template_name}.json"
            }
            templates_export["templates"].append(template_entry)
        
        # Sort templates by name for consistency
        templates_export["templates"].sort(key=lambda x: x["name"])
        
        return json.dumps(templates_export, indent=2), templates_export
    
    def import_templates(self, import_data: str, overwrite_existing: bool = True) -> Tuple[bool, str, List[str], List[str]]:
        """Import base templates from JSON string into session memory only"""
        try:
            # Parse the import data
            parsed_data = json.loads(import_data)
            
            # Validate structure
            if not isinstance(parsed_data, dict):
                return False, "Invalid format: Root must be an object", [], []
            
            if "templates" not in parsed_data:
                return False, "Invalid format: Missing 'templates' array", [], []
            
            if not isinstance(parsed_data["templates"], list):
                return False, "Invalid format: 'templates' must be an array", [], []
            
            imported_templates = []
            skipped_templates = []
            
            # Process each template
            for template_entry in parsed_data["templates"]:
                if not isinstance(template_entry, dict):
                    continue
                
                if "name" not in template_entry or "content" not in template_entry:
                    continue
                
                template_name = template_entry["name"]
                template_content = template_entry["content"]
                
                # Validate template content (basic JSON structure check)
                if not isinstance(template_content, (dict, list)):
                    skipped_templates.append(f"{template_name} (invalid content type)")
                    continue
                
                # Check if template already exists
                if template_name in self.base_templates and not overwrite_existing:
                    skipped_templates.append(f"{template_name} (already exists)")
                    continue
                
                # Save template to session memory only
                if self.save_template(template_name, template_content):
                    imported_templates.append(template_name)
                else:
                    skipped_templates.append(f"{template_name} (session save error)")
            
            message = f"Import completed. {len(imported_templates)} templates imported to session"
            if skipped_templates:
                message += f", {len(skipped_templates)} skipped"
            
            return True, message, imported_templates, skipped_templates
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}", [], []
        except Exception as e:
            return False, f"Import error: {str(e)}", [], []
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get detailed information about a template"""
        if template_name not in self.base_templates:
            return {}
        
        template = self.base_templates[template_name]
        
        info = {
            "size_bytes": len(json.dumps(template)),
            "structure_type": "Object" if isinstance(template, dict) else "Array" if isinstance(template, list) else "Other"
        }
        
        if isinstance(template, dict):
            info["field_count"] = len(template)
            # Get first few field names for preview
            info["fields"] = list(template.keys())[:10]  # Limit to first 10 fields
        elif isinstance(template, list):
            info["field_count"] = len(template)
            info["fields"] = [f"Item {i}" for i in range(min(5, len(template)))]  # Show first 5 items
        else:
            info["field_count"] = 0
            info["fields"] = []
        
        return info
