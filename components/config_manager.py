"""
Configuration manager for handling template-to-endpoint mappings
Supports default configurations and user-customized configurations with session state
"""

import json
import streamlit as st
from typing import Dict, Any, Optional
import os
import re
from copy import deepcopy


# class ConfigurationManager:
#     """Manages template-to-endpoint configuration with session state persistence"""
    
#     def __init__(self, config_file: str = "configuration.json"):
#         self.config_file = config_file
#         self.default_endpoints = {}
#         self.headers = {}
#         self.user_config = {}
#         self.base_url = ""
#         self.shared_token = "Bearer YOUR_API_TOKEN"
#         self.selected_organization = "organization"
#         self.selected_location = "facility"
#         self.load_default_endpoints()
#         self.load_user_config()
        
#     def load_default_endpoints(self):
#         """Load default configuration from JSON file"""
#         try:
#             if os.path.exists(self.config_file):
#                 with open(self.config_file, 'r') as f:
#                     config_data = json.load(f)
#                     # Updated to match bulk_dsg.json structure
#                     self.default_endpoints = config_data.get('endpoints', {})
#                     self.base_url = config_data.get('base_url', 'https://api.example.com')
#                     self.headers = config_data.get('headers', {
#                         'Content-Type': 'application/json',
#                         'Authorization': 'Bearer YOUR_API_TOKEN'
#                     })
                    
#                     # Extract shared token from default headers if available
#                     if 'Authorization' in self.headers:
#                         self.shared_token = self.headers['Authorization']
#                     # Extract organization and facility from default headers if available
#                     if 'SelectedOrganization' in self.headers:
#                         self.selected_organization = self.headers['SelectedOrganization']
#                     if 'SelectedLocation' in self.headers:
#                         self.selected_location = self.headers['SelectedLocation']
#             else:
#                 st.warning(f"Configuration file {self.config_file} not found. Using empty default config.")
#                 self.default_endpoints = {}
#                 self.base_url = 'https://api.example.com'
#                 self.headers = {
#                     'Content-Type': 'application/json',
#                     'Authorization': 'Bearer YOUR_API_TOKEN'
#                 }
#         except Exception as e:
#             st.error(f"Error loading configuration file: {e}")
#             self.default_endpoints = {}
#             self.base_url = 'https://api.example.com'
#             self.headers = {
#                 'Content-Type': 'application/json',
#                 'Authorization': 'Bearer YOUR_API_TOKEN'
#             }
    
#     def load_user_config(self):
#         """Load user-customized configuration from session state"""
#         # Load from session state
#         self.user_config = st.session_state.get('user_endpoint_config', self.default_endpoints)
#         # Load other settings from session state
#         self.base_url = st.session_state.get('base_url', self.base_url)
#         self.shared_token = st.session_state.get('shared_token', self.shared_token)
#         self.selected_organization = st.session_state.get('selected_organization', self.selected_organization)
#         self.selected_location = st.session_state.get('selected_location', self.selected_location)
        
#     def save_user_config(self):
#         """Save user configuration to session state"""
#         # Save to session state
#         st.session_state.user_endpoint_config = self.user_config
#         st.session_state.base_url = self.base_url
#         st.session_state.shared_token = self.shared_token
#         st.session_state.selected_organization = self.selected_organization
#         st.session_state.selected_location = self.selected_location

#     def get_template_config(self, template_name: str) -> Dict[str, Any]:
#         """
#         Get configuration for a specific template
#         User config takes precedence over default config
#         Headers are merged from headers
        
#         Args:
#             template_name: Name of the template
            
#         Returns:
#             Dictionary with endpoint configuration
#         """
#         # Check user config first, then fall back to default
#         if template_name in self.user_config:
#             config = deepcopy(self.user_config[template_name])
#         elif template_name in self.default_endpoints:
#             config = deepcopy(self.default_endpoints[template_name])
#         else:
#             # Return a basic default if template not found
#             config = {
#                 "endpoint": "/data",
#                 "method": "POST",
#                 "description": f"Default endpoint for {template_name}"
#             }
        
#         # Always ensure headers are present by merging with default headers
#         if 'headers' not in config:
#             config['headers'] = deepcopy(getattr(self, 'headers', {
#                 'Content-Type': 'application/json',
#                 'Authorization': self.shared_token
#             }))
#         else:
#             # Merge default headers with template-specific headers
#             merged_headers = deepcopy(getattr(self, 'headers', {}))
#             merged_headers.update(config['headers'])
#             config['headers'] = merged_headers
        
#         return config
    
#     def update_template_config(self, template_name: str, config: Dict[str, Any]):
#         """
#         Update configuration for a specific template
        
#         Args:
#             template_name: Name of the template
#             config: New configuration dictionary
#         """
#         self.user_config[template_name] = config
#         self.save_user_config()
    
#     def reset_template_config(self, template_name: str):
#         """
#         Reset template configuration to default
        
#         Args:
#             template_name: Name of the template to reset
#         """
#         if template_name in self.user_config:
#             del self.user_config[template_name]
#             self.save_user_config()
    
#     def get_all_templates(self) -> list:
#         """Get list of all available templates from both default and user config"""
#         all_templates = set()
#         all_templates.update(self.default_endpoints.keys())
#         all_templates.update(self.user_config.keys())
#         return sorted(list(all_templates))
    
#     def has_custom_config(self, template_name: str) -> bool:
#         """Check if template has custom user configuration"""
#         return template_name in self.user_config
#     def export_full_config(self) -> str:
#         """Export complete configuration including global settings and endpoint configurations"""
#         full_config = {
#             "description": "Template to endpoint mapping configuration",
#             "version": "1.0",
#             "base_url": self.base_url,
#             "headers": {
#                 "Content-Type": "application/json",
#                 "Authorization": self.shared_token,
#                 "SelectedOrganization": self.selected_organization,
#                 "SelectedLocation": self.selected_location
#             },
#             "endpoints": self.user_config
#         }
#         return json.dumps(full_config, indent=2)
    
#     def _import_full_config(self, config_data: dict) -> bool:
#         try:
#             # Handle base_url at the top level (like bulk_dsg.json structure)
#             if "base_url" in config_data:
#                 self.base_url = config_data["base_url"]
            
#             # Handle environment settings from headers section
#             if "headers" in config_data and isinstance(config_data["headers"], dict):
#                 print('found headers')
#                 headers = config_data["headers"]
                
#                 if "Authorization" in headers:
#                     # Use set_shared_token to ensure proper Bearer prefix handling
#                     auth_token = headers["Authorization"]
#                     if auth_token.startswith('Bearer '):
#                         self.shared_token = auth_token
#                     else:
#                         self.set_shared_token(auth_token)
#                 if "SelectedOrganization" in headers:
#                     self.selected_organization = headers["SelectedOrganization"]
#                 if "SelectedLocation" in headers:
#                     self.selected_location = headers["SelectedLocation"]
            
#             # Import endpoint configurations if present
#             if "endpoints" in config_data:
#                 endpoint_configs = config_data["endpoints"]
#                 # Validate endpoint configurations
#                 for template_name, config in endpoint_configs.items():
#                     if not isinstance(config, dict):
#                         raise ValueError(f"Invalid config for template {template_name}")
#                     if 'endpoint' not in config:
#                         raise ValueError(f"Missing endpoint for template {template_name}")
                
#                 self.user_config.update(endpoint_configs)
            
#             # Save all changes
#             self.save_user_config()
#             return True
            
#         except Exception as e:
#             st.error(f"Error importing full configuration: {e}")
#             return False
        
#     def import_full_config(self, config_json: str) -> bool:
#         """
#         Import complete configuration including global settings and endpoint configurations
        
#         Args:
#             config_json: JSON string with full configuration
            
#         Returns:
#             True if successful, False if error
#         """
#         print("🔄 Importing full configuration...")
#         try:
#             imported_config = json.loads(config_json)
#             return self._import_full_config(imported_config)
#         except Exception as e:
#             st.error(f"Error importing full configuration: {e}")
#             raise
#             return False
        
#     def clear_all_user_config(self):
#         """Clear all user customizations from session state"""
#         self.user_config.clear()
        
#         # Clear session state
#         if 'user_endpoint_config' in st.session_state:
#             del st.session_state.user_endpoint_config
#         if 'base_url' in st.session_state:
#             del st.session_state.base_url
#         if 'shared_token' in st.session_state:
#             del st.session_state.shared_token
#         if 'selected_organization' in st.session_state:
#             del st.session_state.selected_organization
#         if 'selected_location' in st.session_state:
#             del st.session_state.selected_location
        
#         # Reset to defaults
#         self.load_default_endpoints()
    
#     def get_base_url(self) -> str:
#         """Get the base URL for API endpoints"""
#         return self.base_url

#     def _validate_base_url(self, base_url: str) -> bool:
#         """
#         Validate base URL to prevent production URLs
        
#         Args:
#             base_url: URL to validate
            
#         Returns:
#             True if URL is safe, False if it's a production URL
            
#         Raises:
#             ValueError: If URL contains production pattern
#         """
#         # Check for 'p' right before '.sce' in the domain
#         production_pattern = r'p\.sce\.'
#         if re.search(production_pattern, base_url, re.IGNORECASE):
#             raise ValueError(
#                 "🚫 PRODUCTION URL DETECTED!\n\n"
#                 "This appears to be a production environment URL (contains 'p.sce.').\n"
#                 "Using this data creation tool on production systems is UNSAFE and PROHIBITED.\n\n"
#                 "Please use a development or test environment URL instead."
#             )
#         return True
    
#     def set_base_url(self, base_url: str):
#         """Set the base URL for API endpoints with production validation"""
#         try:
#             # Validate URL before setting
#             self._validate_base_url(base_url)
#             self.base_url = base_url
#             st.session_state.base_url = base_url
#             # self.save_user_config()
#         except ValueError as e:
#             # Re-raise the validation error to be handled by the UI
#             raise e
    
#     def get_shared_token(self) -> str:
#         """Get the shared API token"""
#         return self.shared_token
    
#     def set_shared_token(self, token: str):
#         """Set the shared API token for all templates"""
#         # Ensure token has Bearer prefix if not already present
#         if not token.startswith('Bearer '):
#             token = f'Bearer {token}'
#         self.shared_token = token
#         st.session_state.shared_token = token
#         # self.save_user_config()
    
#     def get_relative_endpoint_for_template(self, template_name: str) -> str:
#         """Get just the relative endpoint path for a template"""
#         config = self.get_template_config(template_name)
#         return config.get('endpoint', '/data')
    
#     def get_endpoint_for_template(self, template_name: str) -> str:
#         """Get the full endpoint URL for a template"""
#         config = self.get_template_config(template_name)
#         relative_endpoint = config.get('endpoint', '/data')
#         return f"{self.base_url}{relative_endpoint}"
    
#     def get_headers_for_template(self, template_name: str) -> Dict[str, str]:
#         """Get the headers for a template with shared token, organization, and facility"""
#         config = self.get_template_config(template_name)
#         headers = config.get('headers', deepcopy(self.headers)).copy()
        
#         # Always use the shared token, organization, and facility, overriding any template-specific values
#         headers['Authorization'] = self.shared_token
#         headers['SelectedOrganization'] = self.selected_organization
#         headers['SelectedLocation'] = self.selected_location
#         return headers
    
#     def get_method_for_template(self, template_name: str) -> str:
#         """Get HTTP method for a template"""
#         config = self.get_template_config(template_name)
#         return config.get('method', 'POST')
    
#     def get_selected_organization(self) -> str:
#         """Get the selected organization"""
#         return self.selected_organization
    
#     def set_selected_organization(self, organization: str):
#         """Set the selected organization"""
#         self.selected_organization = organization
#         st.session_state.selected_organization = organization
#         # self.save_user_config()
    
#     def get_selected_location(self) -> str:
#         """Get the selected facility"""
#         return self.selected_location
    
#     def set_selected_location(self, facility: str):
#         """Set the selected facility"""
#         self.selected_location = facility
#         st.session_state.selected_location = facility
#         # self.save_user_config()

#     def force_reload_from_session(self):
#         print('🔄 Force reloading configuration from session state')
#         """Force reload all configuration from session state - useful after imports"""
#         self.load_user_config()
#         # Also reload default endpoints if needed
#         if hasattr(st.session_state, 'force_reload_defaults') and st.session_state.force_reload_defaults:
#             self.load_default_endpoints()
#             st.session_state.force_reload_defaults = False
