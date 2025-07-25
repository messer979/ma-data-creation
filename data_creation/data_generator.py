import os
import json
import requests
import streamlit as st
from colorama import Fore, Back, Style, init, just_fix_windows_console

from termcolor import colored

from data_creation.template_generator import TemplateGenerator
from templates.session_base_template_manager import SessionBaseTemplateManager

# Initialize colorama
init(autoreset=True)
just_fix_windows_console()


DEFAULT_API_ENDPOINT = 'https://api.example.com/data'  # Replace with actual endpoint
DEFAULT_API_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_TOKEN'  # Replace with actual token
}


class DataGenerator:
    def __init__(self):
        self.template_generator = TemplateGenerator()
        self.base_template_manager = SessionBaseTemplateManager()
      
    @property
    def templates(self):
        """Get base templates from session-based template manager"""
        return self.base_template_manager.base_templates
    
    def load_templates(self):
        """Reload templates from disk into session"""
        self.base_template_manager.load_templates()
    
    def _load_templates(self):
        """Reload templates from session state (used by template editor reset)"""
        self.base_template_manager.load_templates()
    
    def get_template_generator(self):
        """Get the template generator instance for advanced template operations"""
        return self.template_generator
    
    def has_generation_template(self, template_name: str) -> bool:
        """Check if a generation template exists for the given template name"""
        return template_name in self.template_generator.get_available_templates()
    
    def generate_data(self, template_name: str, count: int = 1, **kwargs) -> list:
        """
        Generate data using generation templates only
        
        Args:
            template_name: Name of the template to use
            count: Number of records to generate
            **kwargs: Additional parameters (ignored, kept for compatibility)
            
        Returns:
            List of generated records
        """
        # Get base template
        base_template = self.templates.get(template_name, {})
        if not base_template:
            raise ValueError(f"Base template '{template_name}' not found")
          # Check if generation template exists
        if not self.has_generation_template(template_name):
            raise ValueError(f"Generation template '{template_name}' not found. Only generation template-based data creation is supported.")
        
        # Use generation template system
        return self.template_generator.generate_records(template_name, count, base_template)

    def send_to_api(self, data, endpoint=None, headers=None, template_config=None):
        """
        Send data to external API with payload wrapping based on template configuration
        
        Args:
            data: The data to send (list of records)
            endpoint: API endpoint URL
            headers: Request headers
            template_config: Template configuration dict containing 'type' and 'dataWrapper' fields
        
        Returns:
            Dictionary with success status and response details
        """
        try:
            url = endpoint or DEFAULT_API_ENDPOINT
            request_headers = headers or DEFAULT_API_HEADERS
            
            # Apply payload wrapping logic based on template configuration
            payload = self._wrap_payload(data, template_config)
            response = requests.post(url, json=payload, headers=request_headers, timeout=30)

            response.raise_for_status()

            return {
                'success': True,
                'status_code': response.status_code,
                'response': response.json() if response.content else {},
                'response_headers': dict(response.headers),
                'response_time': response.elapsed.total_seconds(),
                'request_body': payload
            }
        except requests.exceptions.RequestException as e:
            try:
                response_payload = e.response.json() 
            except requests.exceptions.JSONDecodeError:
                response_payload = e.response.text
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                'response_headers': dict(e.response.headers),
                'response': response_payload,
                'response_time': e.response.elapsed.total_seconds(),
                'request_body': payload
            }
    
    def _wrap_payload(self, data, template_config):
        """
        Wrap payload based on template configuration
        
        Args:
            data: List of records to wrap
            template_config: Configuration dict with 'type' and 'dataWrapper' fields
        
        Returns:
            Wrapped payload based on configuration
        """
        if not template_config:
            return data
        
        payload_type = template_config.get('type')
        data_wrapper = template_config.get('dataWrapper', False)
        
        # Apply wrapping logic based on configuration
        if payload_type == 'xint' and data_wrapper:
            # Both xint and dataWrapper: {"Payload": {"data": [records]}}
            return {"Payload": {"Data": data}}
        elif payload_type == 'xint':
            # Only xint: {"Payload": [records]}
            return {"Payload": data}
        elif data_wrapper:
            # Only dataWrapper: {"data": [records]}
            return {"Data": data}
        else:
            # No wrapping: [records]
            return data
