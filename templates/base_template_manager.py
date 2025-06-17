import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Tuple


import streamlit as st

class BaseTemplateManager:
    """Manages base API templates operations"""
    
    def __init__(self, templates_dir: str = "templates/base_templates"):
        self.templates_dir = templates_dir
        self.base_templates = {}
        self.load_templates()
    
    def load_templates(self):
        """Load all base templates from the templates directory"""
        self.base_templates = {}
        
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            return
        
        # Load all JSON files from templates directory
        template_files = glob.glob(os.path.join(self.templates_dir, "*.json"))
        
        for file_path in template_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    template_data = json.loads(content)
                    
                # Use filename (without extension) as template name
                template_name = os.path.splitext(os.path.basename(file_path))[0]
                self.base_templates[template_name] = template_data
                
            except Exception as e:
                st.error(f"Error loading template {file_path}: {str(e)}")
    
    def save_template(self, template_name: str, template_content: Any) -> bool:
        """Save a template to file"""
        try:
            file_path = os.path.join(self.templates_dir, f"{template_name}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(template_content, f, indent=4, ensure_ascii=False)
            
            # Update in-memory cache
            self.base_templates[template_name] = template_content
            return True
            
        except Exception as e:
            st.error(f"Error saving template {template_name}: {str(e)}")
            return False
    
    def delete_template(self, template_name: str) -> bool:
        """Delete a template file"""
        try:
            file_path = os.path.join(self.templates_dir, f"{template_name}.json")
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Remove from in-memory cache
            if template_name in self.base_templates:
                del self.base_templates[template_name]
            
            return True
            
        except Exception as e:
            st.error(f"Error deleting template {template_name}: {str(e)}")
            return False
    
    def export_all_templates(self) -> Tuple[str, Dict[str, Any]]:
        """Export all base templates as a single JSON structure"""
        templates_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_tool": "Data Creation Tool - Base Template Manager",
                "template_count": len(self.base_templates),
                "export_type": "base_templates"
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
        """Import base templates from JSON string and save to files"""
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
                
                # Save template to file
                if self.save_template(template_name, template_content):
                    imported_templates.append(template_name)
                else:
                    skipped_templates.append(f"{template_name} (save error)")
            
            message = f"Import completed. {len(imported_templates)} templates imported"
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
            "name": template_name,
            "size_bytes": len(json.dumps(template)),
            "field_count": 0,
            "structure_type": type(template).__name__
        }
        
        # Count fields if it's a dictionary
        if isinstance(template, dict):
            info["field_count"] = len(template)
            info["fields"] = list(template.keys())[:10]  # First 10 fields
        elif isinstance(template, list):
            info["field_count"] = len(template)
            info["array_length"] = len(template)
        
        return info

