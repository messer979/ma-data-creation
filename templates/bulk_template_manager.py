import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from data_creation.template_generator import TemplateGenerator

import streamlit as st


class BulkTemplateManager:
    """Manages bulk operations for generation templates"""
    
    @staticmethod
    def export_all_templates(template_generator: TemplateGenerator) -> Tuple[str, Dict[str, Any]]:
        """
        Export all generation templates as a single JSON structure
        
        Args:
            template_generator: TemplateGenerator instance
            
        Returns:
            Tuple of (JSON string, templates dict)
        """
        templates_export = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_tool": "Data Creation Tool - Bulk Template Manager",
                "template_count": len(template_generator.generation_templates)
            },
            "templates": []
        }
        
        # Convert templates to array format with metadata
        for template_name, template_content in template_generator.generation_templates.items():
            template_entry = {
                "name": template_name,
                "content": template_content
            }
            templates_export["templates"].append(template_entry)
        
        # Sort templates by name for consistency
        templates_export["templates"].sort(key=lambda x: x["name"])
        
        return json.dumps(templates_export, indent=2), templates_export
    
    @staticmethod
    def import_all_templates(template_generator: TemplateGenerator, 
                           import_data: str, 
                           overwrite_existing: bool = True) -> Tuple[bool, str, List[str], List[str]]:
        """
        Import generation templates from JSON string into current session (no file writes)
        
        Args:
            template_generator: TemplateGenerator instance
            import_data: JSON string containing templates
            overwrite_existing: Whether to overwrite existing templates
            
        Returns:
            Tuple of (success, message, imported_templates, skipped_templates)
        """
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
                    print(f"Skipping invalid template entry: {template_entry}")
                    continue
                
                if "name" not in template_entry or "content" not in template_entry:
                    print(f"Skipping template with missing name or content fields: {template_entry}")
                    continue
                
                template_name = template_entry["name"]
                template_content = template_entry["content"]
                
                # Validate template content structure
                if not BulkTemplateManager._validate_template_structure(template_content):
                    skipped_templates.append(f"{template_name} (invalid structure)")
                    print(f"Skipping template {template_name} due to _validate_template_structure")
                    continue
                
                # Check if template already exists
                if template_name in template_generator.generation_templates and not overwrite_existing:
                    skipped_templates.append(f"{template_name} (already exists)")
                    print(f"Skipping existing template {template_name} (overwrite not allowed)")
                    continue
                
                # Update template in session memory only (no file write)
                try:
                    template_generator.generation_templates[template_name] = template_content
                    imported_templates.append(template_name)
                    
                except Exception as e:
                    print(f"Error updating template {template_name}: {str(e)}")
                    skipped_templates.append(f"{template_name} (session error: {str(e)})")
            
            # No file reload needed since we're updating session directly
            
            message = f"Import completed. {len(imported_templates)} templates imported to session"
            print(message)
            if skipped_templates:
                message += f", {len(skipped_templates)} skipped"
            
            return True, message, imported_templates, skipped_templates
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}", [], []
        except Exception as e:
            return False, f"Import error: {str(e)}", [], []
    
    @staticmethod
    def _validate_template_structure(template: Any) -> bool:
        """
        Validate that a template has the required structure
        
        Args:
            template: Template content to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(template, dict):
            return False
        
        required_sections = ["StaticFields", "SequenceFields", "RandomFields", "LinkedFields"]
        
        for section in required_sections:
            if section not in template:
                return False
        
        # Validate RandomFields structure
        if not isinstance(template["RandomFields"], list):
            return False
        
        for field in template["RandomFields"]:
            if not isinstance(field, dict) or "FieldName" not in field or "FieldType" not in field:
                return False
        
        # Validate other sections are dicts
        for section in ["StaticFields", "SequenceFields", "LinkedFields"]:
            if not isinstance(template[section], dict):
                return False
        
        return True
