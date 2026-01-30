"""
REST API Service for Data Generation
Provides endpoints to generate data using templates without Streamlit dependency
"""

import os
import json
import glob
import requests
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Import template generation logic
# Note: QueryContext features require Streamlit session state and won't work in API mode
# We'll handle this by checking for QueryContextFields before generation
from data_creation.template_functions import create_record_from_template


class StandaloneTemplateManager:
    """Template manager that works without Streamlit session state"""
    
    def __init__(self, base_templates_dir: str = "templates/base_templates",
                 generation_templates_dir: str = "templates/generation_templates"):
        self.base_templates_dir = base_templates_dir
        self.generation_templates_dir = generation_templates_dir
        self.base_templates = {}
        self.generation_templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from disk"""
        # Load base templates
        if os.path.exists(self.base_templates_dir):
            template_files = glob.glob(os.path.join(self.base_templates_dir, "*.json"))
            for file_path in template_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    template_name = os.path.splitext(os.path.basename(file_path))[0]
                    self.base_templates[template_name] = template_data
                except Exception as e:
                    print(f"Error loading base template {file_path}: {e}")
        
        # Load generation templates
        if os.path.exists(self.generation_templates_dir):
            template_files = glob.glob(os.path.join(self.generation_templates_dir, "*.json"))
            for file_path in template_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    template_name = os.path.splitext(os.path.basename(file_path))[0]
                    self.generation_templates[template_name] = template_data
                except Exception as e:
                    print(f"Error loading generation template {file_path}: {e}")
    
    def get_base_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get base template by name"""
        return self.base_templates.get(template_name)
    
    def get_generation_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get generation template by name"""
        return self.generation_templates.get(template_name)
    
    def add_base_template(self, template_name: str, template_content: Dict[str, Any]):
        """Add a base template (for inline templates)"""
        self.base_templates[template_name] = template_content
    
    def add_generation_template(self, template_name: str, template_content: Dict[str, Any]):
        """Add a generation template (for inline templates)"""
        self.generation_templates[template_name] = template_content
    
    def reload_templates(self):
        """Reload templates from disk (useful after template updates)"""
        self.base_templates = {}
        self.generation_templates = {}
        self._load_templates()
        return {
            "base_templates_loaded": len(self.base_templates),
            "generation_templates_loaded": len(self.generation_templates)
        }


class EndpointConfigurationManager:
    """Manages endpoint configurations from configuration.json"""
    
    def __init__(self, config_file: str = "configuration.json"):
        self.config_file = config_file
        self.base_url = ""
        self.default_headers = {}
        self.endpoints = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load endpoint configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.base_url = config_data.get('base_url', '')
                self.default_headers = config_data.get('headers', {})
                self.endpoints = config_data.get('endpoints', {})
            except Exception as e:
                print(f"Error loading endpoint configuration: {e}")
                self.endpoints = {}
        else:
            print(f"Configuration file {self.config_file} not found")
    
    def get_endpoint_config(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get endpoint configuration for a template"""
        return self.endpoints.get(template_name)
    
    def get_full_endpoint_url(self, template_name: str) -> Optional[str]:
        """Get full endpoint URL for a template"""
        endpoint_config = self.get_endpoint_config(template_name)
        if not endpoint_config:
            return None
        
        endpoint_path = endpoint_config.get('endpoint', '')
        if not endpoint_path:
            return None
        
        # Combine base_url and endpoint path
        if endpoint_path.startswith('http'):
            return endpoint_path
        elif endpoint_path.startswith('/'):
            return self.base_url.rstrip('/') + endpoint_path
        else:
            return self.base_url.rstrip('/') + '/' + endpoint_path
    
    def get_headers(self, template_name: str, 
                   auth_token: Optional[str] = None,
                   header_overrides: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get headers for a template, optionally overriding values
        
        Args:
            template_name: Template name (for future per-template header support)
            auth_token: Optional auth token to override Authorization header
            header_overrides: Optional dict of header key-value pairs to override
        
        Returns:
            Dictionary of headers
        """
        headers = self.default_headers.copy()
        
        # Override Authorization header if auth_token is provided
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        
        # Apply any additional header overrides
        if header_overrides:
            headers.update(header_overrides)
        
        return headers
    
    def get_full_endpoint_url(self, template_name: str, base_url_override: Optional[str] = None, 
                             endpoint_path_override: Optional[str] = None) -> Optional[str]:
        """
        Get full endpoint URL for a template, optionally overriding base_url or endpoint path
        
        Args:
            template_name: Template name
            base_url_override: Optional base URL to override config
            endpoint_path_override: Optional endpoint path to override config
        
        Returns:
            Full endpoint URL
        """
        endpoint_config = self.get_endpoint_config(template_name)
        if not endpoint_config:
            return None
        
        # Use override if provided, otherwise use config
        endpoint_path = endpoint_path_override or endpoint_config.get('endpoint', '')
        if not endpoint_path:
            return None
        
        base_url = base_url_override or self.base_url
        
        # Combine base_url and endpoint path
        if endpoint_path.startswith('http'):
            return endpoint_path
        elif endpoint_path.startswith('/'):
            return base_url.rstrip('/') + endpoint_path
        else:
            return base_url.rstrip('/') + '/' + endpoint_path
    
    def reload_configuration(self):
        """Reload configuration from disk"""
        self._load_configuration()
        return {
            "endpoints_loaded": len(self.endpoints),
            "base_url": self.base_url
        }


def merge_templates(base_template: Dict[str, Any], override_template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge a partial template (override_template) into a base template.
    Deep merges nested dictionaries, replaces arrays, and adds new keys.
    
    Args:
        base_template: The full template from repository
        override_template: Partial template with changes/overrides
        
    Returns:
        Merged template
    """
    from copy import deepcopy
    
    # Start with a deep copy of the base template
    merged = deepcopy(base_template)
    
    # Merge each section from override_template
    for key, value in override_template.items():
        if key == 'template_name':
            # Skip template_name - it's metadata, not part of the template structure
            continue
        elif isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Deep merge dictionaries (e.g., SequenceFields, StaticFields, etc.)
            merged[key].update(value)
        else:
            # Replace arrays or other values entirely, or add new keys
            merged[key] = deepcopy(value)
    
    return merged


class StandaloneTemplateGenerator:
    """Template generator that works without Streamlit"""
    
    def __init__(self, template_manager: StandaloneTemplateManager):
        self.template_manager = template_manager
        from data_creation.sequence_counter_manager import SequenceCounterManager
        self.counter_manager = SequenceCounterManager(use_streamlit=False)
        from data_creation.sequence_counter_manager import SequenceCounterManager
        self.counter_manager = SequenceCounterManager(use_streamlit=False)
    
    def generate_records(self, base_template: Dict[str, Any], 
                        generation_template: Dict[str, Any], 
                        count: int,
                        template_name: Optional[str] = None,
                        use_persistent_counters: bool = True) -> List[Dict[str, Any]]:
        """
        Generate records based on templates
        
        Args:
            base_template: Base JSON template structure
            generation_template: Generation template with rules
            count: Number of records to generate
            template_name: Optional template name for persistent counter tracking
            use_persistent_counters: Whether to use persistent sequence counters (default: True)
            
        Returns:
            List of generated records
        """
        from datetime import datetime
        
        generation_time = datetime.now()
        global_config = {
            "generation_time": generation_time
        }
        
        records = []
        
        # Track sequence field counters across all records
        sequence_fields = generation_template.get('SequenceFields', {})
        sequence_counters = {}
        
        # Use persistent counters if enabled and template_name is provided
        if use_persistent_counters and template_name and self.counter_manager.is_enabled():
            # Initialize counters from persistent storage
            for field_name in sequence_fields.keys():
                current_value = self.counter_manager.get_counter(template_name, field_name)
                if current_value is not None:
                    # Start from the last used value (it will be incremented in the loop)
                    sequence_counters[field_name] = current_value
                else:
                    # Initialize to 0 so first increment gives 1
                    sequence_counters[field_name] = 0
        
        # Shared unique context for tracking uniqueness across ALL records
        shared_unique_context = {}
        
        # Shared array length context for tracking array lengths across ALL records
        shared_array_length_context = {}
        
        for i in range(count):
            record = create_record_from_template(
                base_template,
                generation_template,
                i,
                sequence_counters,
                global_config,
                shared_unique_context,
                shared_array_length_context
            )
            records.append(record)
        
        # Save counters back to persistent storage if enabled
        if use_persistent_counters and template_name and self.counter_manager.is_enabled():
            for field_name, counter_value in sequence_counters.items():
                self.counter_manager.set_counter(template_name, field_name, counter_value)
        
        return records


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Initialize template manager and generator
template_manager = StandaloneTemplateManager()
template_generator = StandaloneTemplateGenerator(template_manager)
endpoint_config_manager = EndpointConfigurationManager()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Data Generation API",
        "base_templates_loaded": len(template_manager.base_templates),
        "generation_templates_loaded": len(template_manager.generation_templates)
    })


@app.route('/api/generate', methods=['POST'])
def generate_data():
    """
    Generate data from templates
    
    Request body:
    {
        "base_template": "template_name" OR { ... template object ... },
        "generation_template": "template_name" OR { ... template object ... },
        "count": 1,
        "template_name": "optional_name_for_inline_templates"
    }
    
    Response:
    {
        "success": true,
        "data": [ ... generated records ... ],
        "count": 1,
        "metadata": { ... }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        # Get base template
        base_template_input = data.get('base_template')
        if not base_template_input:
            return jsonify({
                "success": False,
                "error": "base_template is required"
            }), 400
        
        # Handle base template (name or object)
        if isinstance(base_template_input, str):
            # Template name - load from repo
            base_template = template_manager.get_base_template(base_template_input)
            if not base_template:
                return jsonify({
                    "success": False,
                    "error": f"Base template '{base_template_input}' not found in repository"
                }), 404
            base_template_name = base_template_input
        else:
            # Inline template object
            base_template = base_template_input
            base_template_name = data.get('template_name', 'inline_template')
            template_manager.add_base_template(base_template_name, base_template)
        
        # Get generation template
        generation_template_input = data.get('generation_template')
        if not generation_template_input:
            return jsonify({
                "success": False,
                "error": "generation_template is required"
            }), 400
        
        # Handle generation template (name, object, or partial object with template_name)
        if isinstance(generation_template_input, str):
            # Template name - load from repo
            generation_template = template_manager.get_generation_template(generation_template_input)
            if not generation_template:
                return jsonify({
                    "success": False,
                    "error": f"Generation template '{generation_template_input}' not found in repository"
                }), 404
            counter_template_name = generation_template_input
        else:
            # Check if this is a partial template (has template_name field)
            if isinstance(generation_template_input, dict) and 'template_name' in generation_template_input:
                # Partial template - load base template and merge
                template_name = generation_template_input['template_name']
                base_gen_template = template_manager.get_generation_template(template_name)
                if not base_gen_template:
                    return jsonify({
                        "success": False,
                        "error": f"Generation template '{template_name}' not found in repository for merging"
                    }), 404
                
                # Merge partial template into base template
                generation_template = merge_templates(base_gen_template, generation_template_input)
                counter_template_name = template_name
            else:
                # Full inline template object
                generation_template = generation_template_input
                gen_template_name = data.get('template_name', base_template_name)
                template_manager.add_generation_template(gen_template_name, generation_template)
                counter_template_name = gen_template_name
        
        # Get count
        count = data.get('count', 1)
        if not isinstance(count, int) or count < 1:
            return jsonify({
                "success": False,
                "error": "count must be a positive integer"
            }), 400
        
        # Limit count to prevent abuse
        if count > 1000:
            return jsonify({
                "success": False,
                "error": "count cannot exceed 1000"
            }), 400
        
        # Check if QueryContextFields are used (not supported in API mode)
        if 'QueryContextFields' in generation_template:
            return jsonify({
                "success": False,
                "error": "QueryContextFields are not supported in API mode. Use the Streamlit app or remove QueryContextFields from your template.",
                "hint": "Templates with QueryContextFields require Streamlit session state for query data storage."
            }), 400
        
        # Get persistent counter setting (default: True)
        use_persistent_counters = data.get('use_persistent_counters', True)
        
        # Determine template name for counter tracking
        # Use generation_template name if it's a string, otherwise use base_template name
        if isinstance(generation_template_input, str):
            counter_template_name = generation_template_input
        else:
            counter_template_name = base_template_name
        
        # Generate records
        records = template_generator.generate_records(
            base_template,
            generation_template,
            count,
            template_name=counter_template_name,
            use_persistent_counters=use_persistent_counters
        )
        
        return jsonify({
            "success": True,
            "data": records,
            "count": len(records),
            "metadata": {
                "base_template_source": "repository" if isinstance(base_template_input, str) else "inline",
                "generation_template_source": "repository" if isinstance(generation_template_input, str) else ("partial" if (isinstance(generation_template_input, dict) and 'template_name' in generation_template_input) else "inline"),
                "generated_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/api/templates', methods=['GET'])
def list_templates():
    """List available templates in repository"""
    return jsonify({
        "base_templates": list(template_manager.base_templates.keys()),
        "generation_templates": list(template_manager.generation_templates.keys())
    })


@app.route('/api/templates/<template_type>/<template_name>', methods=['GET'])
def get_template(template_type: str, template_name: str):
    """Get a specific template from repository"""
    if template_type == 'base':
        template = template_manager.get_base_template(template_name)
    elif template_type == 'generation':
        template = template_manager.get_generation_template(template_name)
    else:
        return jsonify({
            "success": False,
            "error": "template_type must be 'base' or 'generation'"
        }), 400
    
    if not template:
        return jsonify({
            "success": False,
            "error": f"Template '{template_name}' not found"
        }), 404
    
    return jsonify({
        "success": True,
        "template_name": template_name,
        "template_type": template_type,
        "template": template
    })


@app.route('/api/templates/reload', methods=['POST'])
def reload_templates():
    """
    Reload templates from disk without restarting the server
    
    Useful when you've updated template files and want changes to take effect
    """
    try:
        result = template_manager.reload_templates()
        return jsonify({
            "success": True,
            "message": "Templates reloaded successfully",
            "base_templates_loaded": result["base_templates_loaded"],
            "generation_templates_loaded": result["generation_templates_loaded"]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/api/endpoints', methods=['GET'])
def list_endpoints():
    """
    List available endpoint configurations
    
    Response includes:
    - base_url: Base URL from configuration
    - default_headers: Default headers from configuration (excluding sensitive tokens)
    - endpoints: Dictionary of endpoint configurations with full URLs
    """
    endpoints_info = {}
    for name, config in endpoint_config_manager.endpoints.items():
        endpoints_info[name] = {
            "endpoint": config.get('endpoint', ''),
            "method": config.get('method', 'POST'),
            "description": config.get('description', ''),
            "type": config.get('type', ''),
            "dataWrapper": config.get('dataWrapper', False),
            "full_url": endpoint_config_manager.get_full_endpoint_url(name)
        }
    
    # Include default headers (but mask sensitive Authorization token)
    default_headers = endpoint_config_manager.default_headers.copy()
    if 'Authorization' in default_headers:
        auth_value = default_headers['Authorization']
        if auth_value and len(auth_value) > 20:
            # Mask token, show first 10 and last 10 characters
            default_headers['Authorization'] = f"{auth_value[:10]}...{auth_value[-10:]}"
    
    return jsonify({
        "success": True,
        "base_url": endpoint_config_manager.base_url,
        "default_headers": default_headers,
        "endpoints": endpoints_info
    })


@app.route('/api/endpoints/reload', methods=['POST'])
def reload_endpoints():
    """Reload endpoint configuration from disk"""
    try:
        result = endpoint_config_manager.reload_configuration()
        return jsonify({
            "success": True,
            "message": "Endpoint configuration reloaded successfully",
            **result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/api/generate-and-send', methods=['POST'])
def generate_and_send():
    """
    Generate data and send it to the configured endpoint
    
    Request body:
    {
        "base_template": "template_name" OR { ... template object ... },
        "generation_template": "template_name" OR { ... template object ... },
        "count": 1,
        "template_name": "optional_name_for_inline_templates",
        "endpoint_template_name": "template_name_from_config",  // Optional: uses template_name if not provided
        "auth_token": "optional_auth_token_to_override_config"  // Optional: overrides Authorization header
    }
    
    Response:
    {
        "success": true,
        "data_generated": [ ... generated records ... ],
        "send_result": { ... API response details ... },
        "count": 1,
        "metadata": { ... }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        # Get base template
        base_template_input = data.get('base_template')
        if not base_template_input:
            return jsonify({
                "success": False,
                "error": "base_template is required"
            }), 400
        
        # Handle base template (name or object)
        if isinstance(base_template_input, str):
            base_template = template_manager.get_base_template(base_template_input)
            if not base_template:
                return jsonify({
                    "success": False,
                    "error": f"Base template '{base_template_input}' not found in repository"
                }), 404
            base_template_name = base_template_input
        else:
            base_template = base_template_input
            base_template_name = data.get('template_name', 'inline_template')
            template_manager.add_base_template(base_template_name, base_template)
        
        # Get generation template
        generation_template_input = data.get('generation_template')
        if not generation_template_input:
            return jsonify({
                "success": False,
                "error": "generation_template is required"
            }), 400
        
        # Handle generation template (name, object, or partial object with template_name)
        if isinstance(generation_template_input, str):
            # Template name - load from repo
            generation_template = template_manager.get_generation_template(generation_template_input)
            if not generation_template:
                return jsonify({
                    "success": False,
                    "error": f"Generation template '{generation_template_input}' not found in repository"
                }), 404
            counter_template_name = generation_template_input
        else:
            # Check if this is a partial template (has template_name field)
            if isinstance(generation_template_input, dict) and 'template_name' in generation_template_input:
                # Partial template - load base template and merge
                template_name = generation_template_input['template_name']
                base_gen_template = template_manager.get_generation_template(template_name)
                if not base_gen_template:
                    return jsonify({
                        "success": False,
                        "error": f"Generation template '{template_name}' not found in repository for merging"
                    }), 404
                
                # Merge partial template into base template
                generation_template = merge_templates(base_gen_template, generation_template_input)
                counter_template_name = template_name
            else:
                # Full inline template object
                generation_template = generation_template_input
                gen_template_name = data.get('template_name', base_template_name)
                template_manager.add_generation_template(gen_template_name, generation_template)
                counter_template_name = gen_template_name
        
        # Get count
        count = data.get('count', 1)
        if not isinstance(count, int) or count < 1:
            return jsonify({
                "success": False,
                "error": "count must be a positive integer"
            }), 400
        
        if count > 1000:
            return jsonify({
                "success": False,
                "error": "count cannot exceed 1000"
            }), 400
        
        # Check if QueryContextFields are used (not supported in API mode)
        if 'QueryContextFields' in generation_template:
            return jsonify({
                "success": False,
                "error": "QueryContextFields are not supported in API mode. Use the Streamlit app or remove QueryContextFields from your template.",
                "hint": "Templates with QueryContextFields require Streamlit session state for query data storage."
            }), 400
        
        # Get persistent counter setting (default: True)
        use_persistent_counters = data.get('use_persistent_counters', True)
        
        # counter_template_name is already set above based on the template type
        
        # Generate records
        records = template_generator.generate_records(
            base_template,
            generation_template,
            count,
            template_name=counter_template_name,
            use_persistent_counters=use_persistent_counters
        )
        
        # Get endpoint configuration
        endpoint_template_name = data.get('endpoint_template_name', base_template_name)
        endpoint_config = endpoint_config_manager.get_endpoint_config(endpoint_template_name)
        
        if not endpoint_config:
            return jsonify({
                "success": False,
                "error": f"Endpoint configuration not found for template '{endpoint_template_name}'. Available endpoints: {list(endpoint_config_manager.endpoints.keys())}",
                "hint": "Use GET /api/endpoints to see available endpoint configurations"
            }), 404
        
        # Get endpoint URL (with optional overrides)
        base_url_override = data.get('base_url')
        endpoint_path_override = data.get('endpoint_path')
        endpoint_url = endpoint_config_manager.get_full_endpoint_url(
            endpoint_template_name,
            base_url_override=base_url_override,
            endpoint_path_override=endpoint_path_override
        )
        if not endpoint_url:
            return jsonify({
                "success": False,
                "error": f"Could not construct endpoint URL for template '{endpoint_template_name}'"
            }), 500
        
        # Get headers (with optional overrides)
        auth_token = data.get('auth_token')
        header_overrides = {}
        
        # Allow overriding specific headers (support both camelCase and PascalCase)
        if 'selectedOrganization' in data or 'SelectedOrganization' in data:
            header_overrides['SelectedOrganization'] = data.get('selectedOrganization') or data.get('SelectedOrganization')
        if 'selectedLocation' in data or 'SelectedLocation' in data:
            header_overrides['SelectedLocation'] = data.get('selectedLocation') or data.get('SelectedLocation')
        
        # Allow overriding any other headers via headers object
        if 'headers' in data and isinstance(data['headers'], dict):
            header_overrides.update(data['headers'])
        
        headers = endpoint_config_manager.get_headers(
            endpoint_template_name, 
            auth_token=auth_token,
            header_overrides=header_overrides if header_overrides else None
        )
        
        # Wrap payload based on template configuration
        payload = _wrap_payload(records, endpoint_config)
        
        # Debug logging (can be removed in production)
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        
        print(f"[DEBUG] Endpoint URL: {endpoint_url}")
        print(f"[DEBUG] Endpoint Config: {json.dumps(endpoint_config, indent=2)}")
        print(f"[DEBUG] Payload structure: {type(payload)}")
        if isinstance(payload, dict):
            print(f"[DEBUG] Payload keys: {list(payload.keys())}")
            if 'Payload' in payload:
                if isinstance(payload['Payload'], dict):
                    print(f"[DEBUG] Payload.Payload keys: {list(payload['Payload'].keys())}")
                    if 'Data' in payload['Payload']:
                        print(f"[DEBUG] Records count in Payload.Data: {len(payload['Payload']['Data'])}")
                elif isinstance(payload['Payload'], list):
                    print(f"[DEBUG] Records count in Payload: {len(payload['Payload'])}")
            elif 'Data' in payload:
                print(f"[DEBUG] Records count in Data: {len(payload['Data'])}")
        elif isinstance(payload, list):
            print(f"[DEBUG] Records count in list: {len(payload)}")
        
        # Log first record structure for debugging
        if isinstance(payload, dict) and 'Payload' in payload:
            if isinstance(payload['Payload'], dict) and 'Data' in payload['Payload']:
                if payload['Payload']['Data']:
                    print(f"[DEBUG] First record keys: {list(payload['Payload']['Data'][0].keys())[:10]}")
            elif isinstance(payload['Payload'], list) and payload['Payload']:
                print(f"[DEBUG] First record keys: {list(payload['Payload'][0].keys())[:10]}")
        elif isinstance(payload, dict) and 'Data' in payload:
            if payload['Data']:
                print(f"[DEBUG] First record keys: {list(payload['Data'][0].keys())[:10]}")
        elif isinstance(payload, list) and payload:
            print(f"[DEBUG] First record keys: {list(payload[0].keys())[:10]}")
        
        print(f"[DEBUG] Headers (masked): {json.dumps({k: (v[:20] + '...' if isinstance(v, str) and len(v) > 20 else v) for k, v in headers.items()}, indent=2)}")
        
        # Send to endpoint
        method = endpoint_config.get('method', 'POST').upper()
        timeout = 30
        
        try:
            if method == 'POST':
                response = requests.post(endpoint_url, json=payload, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(endpoint_url, json=payload, headers=headers, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(endpoint_url, json=payload, headers=headers, timeout=timeout)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Unsupported HTTP method: {method}"
                }), 400
            
            response.raise_for_status()
            
            # Parse response - handle both JSON and non-JSON responses
            response_data = {}
            if response.content:
                try:
                    response_data = response.json()
                except (ValueError, requests.exceptions.JSONDecodeError):
                    # Response is not JSON, return as text
                    response_data = response.text
            
            send_result = {
                'success': True,
                'status_code': response.status_code,
                'response': response_data,
                'response_headers': dict(response.headers),
                'response_time': response.elapsed.total_seconds(),
                'request_url': endpoint_url,
                'request_method': method,
                'request_payload': payload  # Include payload for debugging
            }
        except requests.exceptions.RequestException as e:
            try:
                response_payload = e.response.json() if hasattr(e, 'response') and e.response else {}
            except (requests.exceptions.JSONDecodeError, AttributeError):
                response_payload = e.response.text if hasattr(e, 'response') and e.response else str(e)
            
            send_result = {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                'response_headers': dict(e.response.headers) if hasattr(e, 'response') and e.response else {},
                'response': response_payload,
                'response_time': getattr(e.response, 'elapsed', None).total_seconds() if hasattr(e, 'response') and hasattr(e.response, 'elapsed') else None,
                'request_url': endpoint_url,
                'request_method': method
            }
        
        return jsonify({
            "success": True,
            "data_generated": records,
            "send_result": send_result,
            "count": len(records),
            "metadata": {
                "base_template_source": "repository" if isinstance(base_template_input, str) else "inline",
                "generation_template_source": "repository" if isinstance(generation_template_input, str) else ("partial" if (isinstance(generation_template_input, dict) and 'template_name' in generation_template_input) else "inline"),
                "endpoint_template_name": endpoint_template_name,
                "endpoint_url": endpoint_url,
                "generated_at": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/api/sequence-counters', methods=['GET'])
def get_sequence_counters():
    """
    Get all sequence counter values, optionally filtered by template name
    
    Query parameters:
    - template_name: Optional template name to filter by
    
    Response:
    {
        "success": true,
        "counters": {
            "template_name::field_name": counter_value,
            ...
        }
    }
    """
    template_name = request.args.get('template_name')
    
    counters = template_generator.counter_manager.get_all_counters(template_name)
    
    # Format response with template and field names separated
    formatted_counters = {}
    for key, value in counters.items():
        if '::' in key:
            template, field = key.split('::', 1)
            if template not in formatted_counters:
                formatted_counters[template] = {}
            formatted_counters[template][field] = value
        else:
            formatted_counters[key] = value
    
    return jsonify({
        "success": True,
        "counters": formatted_counters,
        "raw_counters": counters
    })


@app.route('/api/sequence-counters/<template_name>', methods=['GET'])
def get_template_sequence_counters(template_name: str):
    """
    Get sequence counter values for a specific template
    
    Response:
    {
        "success": true,
        "template_name": "ndc_asn_cas",
        "counters": {
            "AsnId": 5,
            "Lpn.LpnId": 10,
            ...
        }
    }
    """
    counters = template_generator.counter_manager.get_template_counters(template_name)
    
    return jsonify({
        "success": True,
        "template_name": template_name,
        "counters": counters
    })


@app.route('/api/sequence-counters/<template_name>', methods=['DELETE'])
def reset_template_sequence_counters(template_name: str):
    """
    Reset sequence counters for a specific template
    
    Response:
    {
        "success": true,
        "message": "Sequence counters reset for template 'ndc_asn_cas'"
    }
    """
    template_generator.counter_manager.reset_counters(template_name)
    
    return jsonify({
        "success": True,
        "message": f"Sequence counters reset for template '{template_name}'"
    })


@app.route('/api/sequence-counters', methods=['DELETE'])
def reset_all_sequence_counters():
    """
    Reset all sequence counters
    
    Response:
    {
        "success": true,
        "message": "All sequence counters reset"
    }
    """
    template_generator.counter_manager.reset_counters()
    
    return jsonify({
        "success": True,
        "message": "All sequence counters reset"
    })


@app.route('/api/sequence-counters/enabled', methods=['GET'])
def get_counter_enabled():
    """Get whether persistent sequence counters are enabled"""
    return jsonify({
        "success": True,
        "enabled": template_generator.counter_manager.is_enabled()
    })


@app.route('/api/sequence-counters/enabled', methods=['POST'])
def set_counter_enabled():
    """
    Enable or disable persistent sequence counters
    
    Request body:
    {
        "enabled": true
    }
    """
    data = request.get_json()
    enabled = data.get('enabled', True)
    
    template_generator.counter_manager.set_enabled(enabled)
    
    return jsonify({
        "success": True,
        "enabled": enabled,
        "message": f"Persistent sequence counters {'enabled' if enabled else 'disabled'}"
    })


@app.route('/api/endpoints/config', methods=['GET'])
def get_endpoint_config():
    """
    Get current endpoint configuration (base_url and default headers)
    
    Response:
    {
        "success": true,
        "base_url": "...",
        "default_headers": { ... },
        "endpoint_count": 12
    }
    """
    # Include default headers (but mask sensitive Authorization token)
    default_headers = endpoint_config_manager.default_headers.copy()
    if 'Authorization' in default_headers:
        auth_value = default_headers['Authorization']
        if auth_value and len(auth_value) > 20:
            # Mask token, show first 10 and last 10 characters
            default_headers['Authorization'] = f"{auth_value[:10]}...{auth_value[-10:]}"
    
    return jsonify({
        "success": True,
        "base_url": endpoint_config_manager.base_url,
        "default_headers": default_headers,
        "endpoint_count": len(endpoint_config_manager.endpoints)
    })


@app.route('/api/endpoints/config', methods=['POST'])
def update_endpoint_config():
    """
    Update endpoint configuration for the current session (does not modify configuration.json)
    
    Request body:
    {
        "base_url": "https://new-url.com",  // Optional
        "headers": {  // Optional - will merge with existing headers
            "SelectedOrganization": "MA-038",
            "SelectedLocation": "MA-038",
            "Authorization": "Bearer token..."
        }
    }
    
    Response:
    {
        "success": true,
        "message": "Configuration updated",
        "base_url": "...",
        "default_headers": { ... }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        # Update base_url if provided
        if 'base_url' in data:
            endpoint_config_manager.base_url = data['base_url']
        
        # Update headers if provided (merge with existing)
        if 'headers' in data and isinstance(data['headers'], dict):
            endpoint_config_manager.default_headers.update(data['headers'])
        
        # Include updated headers in response (but mask sensitive Authorization token)
        default_headers = endpoint_config_manager.default_headers.copy()
        if 'Authorization' in default_headers:
            auth_value = default_headers['Authorization']
            if auth_value and len(auth_value) > 20:
                default_headers['Authorization'] = f"{auth_value[:10]}...{auth_value[-10:]}"
        
        return jsonify({
            "success": True,
            "message": "Endpoint configuration updated for this session",
            "base_url": endpoint_config_manager.base_url,
            "default_headers": default_headers,
            "note": "Changes are session-only and will be lost when the server restarts. Use configuration.json for permanent changes."
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/api/endpoints/<endpoint_name>', methods=['GET'])
def get_endpoint_details(endpoint_name: str):
    """
    Get detailed information about a specific endpoint
    
    Response:
    {
        "success": true,
        "endpoint_name": "...",
        "endpoint": "/path/to/endpoint",
        "method": "POST",
        "type": "xint",
        "dataWrapper": true,
        "description": "...",
        "full_url": "https://...",
        "default_headers": { ... }
    }
    """
    endpoint_config = endpoint_config_manager.get_endpoint_config(endpoint_name)
    
    if not endpoint_config:
        return jsonify({
            "success": False,
            "error": f"Endpoint '{endpoint_name}' not found"
        }), 404
    
    # Include default headers (but mask sensitive Authorization token)
    default_headers = endpoint_config_manager.default_headers.copy()
    if 'Authorization' in default_headers:
        auth_value = default_headers['Authorization']
        if auth_value and len(auth_value) > 20:
            default_headers['Authorization'] = f"{auth_value[:10]}...{auth_value[-10:]}"
    
    return jsonify({
        "success": True,
        "endpoint_name": endpoint_name,
        "endpoint": endpoint_config.get('endpoint', ''),
        "method": endpoint_config.get('method', 'POST'),
        "type": endpoint_config.get('type', ''),
        "dataWrapper": endpoint_config.get('dataWrapper', False),
        "description": endpoint_config.get('description', ''),
        "full_url": endpoint_config_manager.get_full_endpoint_url(endpoint_name),
        "default_headers": default_headers
    })


def _wrap_payload(data: List[Dict[str, Any]], template_config: Dict[str, Any]) -> Any:
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
        # Both xint and dataWrapper: {"Payload": {"Data": [records]}}
        return {"Payload": {"Data": data}}
    elif payload_type == 'xint':
        # Only xint: {"Payload": [records]}
        return {"Payload": data}
    elif data_wrapper:
        # Only dataWrapper: {"Data": [records]}
        return {"Data": data}
    else:
        # No wrapping: [records]
        return data


if __name__ == '__main__':
    # Run the API server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Data Generation API on port {port}")
    print(f"Available base templates: {list(template_manager.base_templates.keys())}")
    print(f"Available generation templates: {list(template_manager.generation_templates.keys())}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
