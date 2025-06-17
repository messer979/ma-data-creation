"""
Template-based data generation engine
Interprets generation templates to create randomized data with controlled patterns
Session-only storage - loads example generation templates on startup
"""

import json
import os
import glob
import streamlit as st
from typing import Dict, Any, List, Optional
from data_creation.template_functions import create_record_from_template


class TemplateGenerator:
    """Generates data based on generation template specifications - session only with examples"""
    
    def __init__(self, generation_templates_dir: str = "templates/generation_templates"):
        self.templates_dir = generation_templates_dir
        self.session_key = "session_generation_templates"
        self.examples_loaded_key = "session_generation_examples_loaded"
        self._ensure_session_templates()
    
    def _ensure_session_templates(self):
        """Ensure session state has generation templates initialized and load examples"""
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = {}
        
        # Load example generation templates on first initialization
        if not st.session_state.get(self.examples_loaded_key, False):
            self._load_example_generation_templates()
            st.session_state[self.examples_loaded_key] = True
    
    def _load_example_generation_templates(self):
        """Load example generation templates from disk into session"""
        if not os.path.exists(self.templates_dir):
            return
        
        # Load all JSON files from generation templates directory
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
    def generation_templates(self) -> Dict[str, Any]:
        """Get generation templates from session state"""
        self._ensure_session_templates()
        return st.session_state[self.session_key]
    
    def load_generation_templates(self):
        """Reload example generation templates from disk"""
        self._load_example_generation_templates()
    
    def generate_records(self, template_name: str, count: int, base_template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate records based on generation template using functional approach
        
        Args:
            template_name: Name of the generation template
            count: Number of records to generate
            base_template: Base JSON template structure
            
        Returns:
            List of generated records
        """
        if template_name not in self.generation_templates:
            raise ValueError(f"Generation template '{template_name}' not found")
        
        generation_template = self.generation_templates[template_name]
        records = []
        
        # Track dynamic field counters across all records
        dynamic_counters = {}
        
        for i in range(count):
            record = create_record_from_template(
                base_template,
                generation_template,
                i,
                dynamic_counters
            )
            records.append(record)
        
        return records
    
    def get_available_templates(self) -> List[str]:
        """Get list of available generation templates"""
        return list(self.generation_templates.keys())
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific generation template"""
        return self.generation_templates.get(template_name)
