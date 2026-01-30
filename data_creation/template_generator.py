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
from datetime import datetime, timedelta

from data_creation.template_functions import create_record_from_template
from data_creation.sequence_counter_manager import SequenceCounterManager
from colorama import Fore, Back, Style, init, just_fix_windows_console
from termcolor import colored
# Initialize colorama
init(autoreset=True)
just_fix_windows_console()


class TemplateGenerator:
    """Generates data based on generation template specifications - session only with examples"""
    
    def __init__(self, generation_templates_dir: str = "templates/generation_templates"):
        self.templates_dir = generation_templates_dir
        self.session_key = "session_generation_templates"
        self.examples_loaded_key = "session_generation_examples_loaded"
        self.counter_manager = SequenceCounterManager(use_streamlit=True)
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
        generation_time = datetime.now()
        if template_name not in self.generation_templates:
            raise ValueError(f"Generation template '{template_name}' not found")
        global_config = {
            "generation_time": generation_time
        }
        generation_template = self.generation_templates[template_name]
        records = []
        
        # Track sequence field counters across all records
        # Use persistent counters if enabled, otherwise use local dict
        sequence_fields = generation_template.get('SequenceFields', {})
        sequence_counters = {}
        
        if self.counter_manager.is_enabled():
            # Initialize counters from persistent storage
            # Start from the last used value, so next increment will be correct
            for field_name in sequence_fields.keys():
                current_value = self.counter_manager.get_counter(template_name, field_name)
                if current_value is not None:
                    # Start from the last used value (it will be incremented in the loop)
                    sequence_counters[field_name] = current_value
                else:
                    # Initialize to 0 so first increment gives 1
                    sequence_counters[field_name] = 0
        else:
            # Not using persistent counters - initialize to empty (will start at 1 on first use)
            pass
        
        # Shared unique context for tracking uniqueness across ALL records
        shared_unique_context = {}
        
        # ENHANCEMENT 2: Shared context for choiceOrder array lengths across all records
        array_length_choice_context = {}
        
        for i in range(count):
            record = create_record_from_template(
                base_template,
                generation_template,
                i,
                sequence_counters,
                global_config,
                shared_unique_context,  # Pass the shared context to maintain uniqueness across records
                array_length_choice_context  # Pass shared context for array length choiceOrder
            )
            records.append(record)
        
        # Save counters back to persistent storage if enabled
        if self.counter_manager.is_enabled():
            for field_name, counter_value in sequence_counters.items():
                self.counter_manager.set_counter(template_name, field_name, counter_value)
        
        return records
    
    def get_available_templates(self) -> List[str]:
        """Get list of available generation templates"""
        return list(self.generation_templates.keys())
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific generation template"""
        return self.generation_templates.get(template_name)
