# Data Generation API Service

A REST API service that generates test data using base templates and generation templates. This service can be used independently of the Streamlit web application.

## Features

- ✅ Generate data from templates stored in repository
- ✅ Generate data from inline template objects (pass full templates in request)
- ✅ Support for all generation template features:
  - StaticFields
  - SequenceFields (with underscore control, attribute references, and substr() function)
  - ArrayLengths (static and variable with int(min,max) and choiceOrder)
  - RandomFields
  - LinkedFields
- ✅ Persistent sequence counters - prevent duplicate keys across generation requests
- ✅ Endpoint configuration management - view and update headers, URLs dynamically
- ⚠️ QueryContextFields: Not supported in API mode (requires Streamlit session state)
- ✅ CORS enabled for cross-origin requests
- ✅ Health check endpoint
- ✅ Template listing and retrieval endpoints

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure templates are in the correct directories:
- Base templates: `templates/base_templates/`
- Generation templates: `templates/generation_templates/`

## Running the API

### Development Mode
```bash
python api_service.py
```

The API will start on `http://localhost:5000`

### Production Mode
```bash
# Set environment variables
export PORT=5000
export DEBUG=False

# Run with a production WSGI server (e.g., gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 api_service:app
```

## API Endpoints

### Health Check
```
GET /health
```

Returns service status and template counts.

**Response:**
```json
{
  "status": "healthy",
  "service": "Data Generation API",
  "base_templates_loaded": 15,
  "generation_templates_loaded": 15
}
```

### List Endpoints
```
GET /api/endpoints
```

List all available endpoint configurations from `configuration.json`.

**Response:**
```json
{
  "success": true,
  "base_url": "https://tests.sc.ma.co",
  "endpoints": {
    "ndc_asn_cas": {
      "endpoint": "/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
      "method": "POST",
      "description": "ASN LPN Level data endpoint",
      "full_url": "https://tests.sc.ma.co/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn"
    }
  }
}
```

### Reload Endpoints
```
POST /api/endpoints/reload
```

Reload endpoint configuration from `configuration.json` without restarting the server.

**Response:**
```json
{
  "success": true,
  "message": "Endpoint configuration reloaded successfully",
  "endpoints_loaded": 12,
  "base_url": "https://tests.sc.ma.co"
}
```

### Generate Data
```
POST /api/generate
```

Generate data using templates. Supports three ways to specify templates:
1. **Template names** - Use templates from repository
2. **Full inline templates** - Pass complete template objects
3. **Partial templates** - Override specific sections of a repository template

**Request Body:**
```json
{
  "base_template": "ndc_asn_cas",  // Template name OR full template object
  "generation_template": "ndc_asn_cas",  // Template name OR full template object OR partial template
  "count": 5,
  "template_name": "optional_name"  // Only needed for inline templates
}
```

**Partial Template Example:**
Override specific sections of a repository template by including a `template_name` field:
```json
{
  "base_template": "ndc_asn_cas",
  "generation_template": {
    "template_name": "ndc_asn_cas",  // Load this template from repository
    "SequenceFields": {
      "AsnId": "BGNDC{{dttm}}*"  // Override only this field
    }
  },
  "count": 1
}
```

This will:
- Load the full `ndc_asn_cas` generation template from the repository
- Merge the provided `SequenceFields` section (replacing/adding `AsnId`)
- Use all other sections from the repository template (StaticFields, ArrayLengths, RandomFields, LinkedFields, etc.)

**Response:**
```json
{
  "success": true,
  "data": [
    { ... generated record 1 ... },
    { ... generated record 2 ... },
    ...
  ],
  "count": 5,
  "metadata": {
    "base_template_source": "repository",
    "generation_template_source": "repository",
    "generated_at": "2026-01-27T10:30:00"
  }
}
```

### List Endpoints
```
GET /api/endpoints
```

List all available endpoint configurations from `configuration.json`.

**Response:**
```json
{
  "success": true,
  "base_url": "https://tests.sc.ma.co",
  "default_headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJhbGc...token...masked",
    "SelectedOrganization": "MA-038",
    "SelectedLocation": "MA-038"
  },
  "endpoints": {
    "asn_lpn_level": {
      "endpoint": "/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
      "method": "POST",
      "type": "xint",
      "dataWrapper": true,
      "description": "ASN LPN Level data endpoint",
      "full_url": "https://tests.sc.ma.co/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn"
    }
  }
}
```

**Note:** Authorization tokens in `default_headers` are masked for security (shows first 10 and last 10 characters).

### Reload Endpoints
```
POST /api/endpoints/reload
```

Reload endpoint configuration from `configuration.json` without restarting the server.

**Response:**
```json
{
  "success": true,
  "message": "Endpoint configuration reloaded successfully",
  "endpoints_loaded": 12,
  "base_url": "https://tests.sc.ma.co"
}
```

### Get Endpoint Configuration
```
GET /api/endpoints/config
```

Get current endpoint configuration (base_url and default headers).

**Response:**
```json
{
  "success": true,
  "base_url": "https://tests.sc.ma.co",
  "default_headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer eyJhbGc...token...masked",
    "SelectedOrganization": "MA-038",
    "SelectedLocation": "MA-038"
  },
  "endpoint_count": 12
}
```

### Update Endpoint Configuration
```
POST /api/endpoints/config
```

Update endpoint configuration for the current session (does not modify `configuration.json`).

**Request Body:**
```json
{
  "base_url": "https://new-url.com",
  "headers": {
    "SelectedOrganization": "MA-038",
    "SelectedLocation": "MA-038",
    "Authorization": "Bearer new_token_here"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Endpoint configuration updated for this session",
  "base_url": "https://new-url.com",
  "default_headers": { ... },
  "note": "Changes are session-only and will be lost when the server restarts. Use configuration.json for permanent changes."
}
```

### Get Endpoint Details
```
GET /api/endpoints/<endpoint_name>
```

Get detailed information about a specific endpoint.

**Response:**
```json
{
  "success": true,
  "endpoint_name": "asn_lpn_level",
  "endpoint": "/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
  "method": "POST",
  "type": "xint",
  "dataWrapper": true,
  "description": "ASN LPN Level data endpoint",
  "full_url": "https://tests.sc.ma.co/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
  "default_headers": { ... }
}
```

### Generate and Send Data
```
POST /api/generate-and-send
```

Generate data using templates and automatically send it to the configured endpoint.

**Request Body:**
```json
{
  "base_template": "ndc_asn_cas",
  "generation_template": "ndc_asn_cas",
  "count": 1,
  "endpoint_template_name": "asn_lpn_level",
  "auth_token": "your_auth_token_here",
  "base_url": "https://custom-url.com",
  "endpoint_path": "/custom/path",
  "selectedOrganization": "MA-038",
  "selectedLocation": "MA-038",
  "headers": {
    "Custom-Header": "value"
  }
}
```

**Partial Template Example:**
```json
{
  "base_template": "ndc_asn_cas",
  "generation_template": {
    "template_name": "ndc_asn_cas",
    "SequenceFields": {
      "AsnId": "BGNDC{{dttm}}*"
    }
  },
  "count": 1,
  "endpoint_template_name": "asn_lpn_level",
  "auth_token": "your_auth_token_here"
}
```

**Parameters:**
- `base_template`: Template name OR full template object (required)
- `generation_template`: Template name OR full template object OR partial template object (required)
  - **Template name**: String like `"ndc_asn_cas"` - loads from repository
  - **Full template**: Complete template object with all sections
  - **Partial template**: Template object with `template_name` field - merges with repository template
    ```json
    {
      "template_name": "ndc_asn_cas",
      "SequenceFields": {
        "AsnId": "BGNDC{{dttm}}*"
      }
    }
    ```
- `count`: Number of records to generate (required, 1-1000)
- `template_name`: Optional name for inline templates
- `endpoint_template_name`: Optional - template name from `configuration.json` to use for endpoint config (defaults to `base_template` name)
- `auth_token`: Optional - auth token to override the one in `configuration.json`
- `base_url`: Optional - base URL to override the one in `configuration.json`
- `endpoint_path`: Optional - endpoint path to override the one in endpoint config
- `selectedOrganization` or `SelectedOrganization`: Optional - override SelectedOrganization header
- `selectedLocation` or `SelectedLocation`: Optional - override SelectedLocation header
- `headers`: Optional - dictionary of additional headers to override/add

**Response:**
```json
{
  "success": true,
  "data_generated": [ ... generated records ... ],
  "send_result": {
    "success": true,
    "status_code": 200,
    "response": { ... API response ... },
    "response_headers": { ... },
    "response_time": 0.234,
    "request_url": "https://tests.sc.ma.co/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
    "request_method": "POST"
  },
  "count": 1,
  "metadata": {
    "base_template_source": "repository",
    "generation_template_source": "repository",
    "endpoint_template_name": "asn_lpn_level",
    "endpoint_url": "https://tests.sc.ma.co/xint/api/async/outbound/send?messageType=ANY_RCV_ImportAsn",
    "generated_at": "2024-01-15T10:30:00"
  }
}
```

**Error Response (Endpoint Not Found):**
```json
{
  "success": false,
  "error": "Endpoint configuration not found for template 'ndc_asn_cas'. Available endpoints: ['facility', 'item', 'vendor', 'po', 'asn_lpn_level', ...]",
  "hint": "Use GET /api/endpoints to see available endpoint configurations"
}
```

**Notes:**
- The endpoint configuration is loaded from `configuration.json` in the repository root
- If `auth_token` is provided, it overrides the `Authorization` header from the configuration
- Payload wrapping is automatically applied based on the endpoint configuration (`type` and `dataWrapper` fields)
- The endpoint supports POST, PUT, and PATCH methods (as configured)

### List Templates
```
GET /api/templates
```

List all available templates in the repository.

**Response:**
```json
{
  "base_templates": ["ndc_asn_cas", "ndc_asn_pcl", ...],
  "generation_templates": ["ndc_asn_cas", "ndc_asn_pcl", ...]
}
```

### Get Template
```
GET /api/templates/<template_type>/<template_name>
```

Get a specific template from the repository.

**Parameters:**
- `template_type`: `base` or `generation`
- `template_name`: Name of the template

**Response:**
```json
{
  "success": true,
  "template_name": "ndc_asn_cas",
  "template_type": "base",
  "template": { ... template content ... }
}
```

### Reload Templates
```
POST /api/templates/reload
```

Reload templates from disk without restarting the server. Use this after updating template files.

**Response:**
```json
{
  "success": true,
  "message": "Templates reloaded successfully",
  "base_templates_loaded": 15,
  "generation_templates_loaded": 15
}
```

## Usage Examples

### Example 1: Using Template Names (from Repository)

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "base_template": "ndc_asn_cas",
    "generation_template": "ndc_asn_cas",
    "count": 3
  }'
```

### Example 2: Using Inline Templates

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "base_template": {
      "AsnId": null,
      "DestinationFacilityId": null,
      "Lpn": [{"LpnId": null}]
    },
    "generation_template": {
      "StaticFields": {
        "DestinationFacilityId": "MA-038"
      },
      "SequenceFields": {
        "AsnId": "TEST{{dt}}"
      },
      "ArrayLengths": {
        "Lpn": 1
      }
    },
    "count": 2,
    "template_name": "custom_template"
  }'
```

### Example 3: Mixed (Base from Repo, Generation Inline)

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "base_template": "ndc_asn_cas",
    "generation_template": {
      "StaticFields": {
        "DestinationFacilityId": "CUSTOM-001"
      },
      "SequenceFields": {
        "AsnId": "CUSTOM{{dt}}"
      }
    },
    "count": 1
  }'
```

### Example 4: Partial Template (Override Specific Sections)

Override specific sections of a repository template by including a `template_name` field:

```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "base_template": "ndc_asn_cas",
    "generation_template": {
      "template_name": "ndc_asn_cas",
      "SequenceFields": {
        "AsnId": "BGNDC{{dttm}}*"
      }
    },
    "count": 1
  }'
```

This will:
- Load the full `ndc_asn_cas` generation template from the repository
- Merge the provided `SequenceFields` section (replacing/adding `AsnId`)
- Use all other sections from the repository template (StaticFields, ArrayLengths, RandomFields, LinkedFields, etc.)

**Partial Template Benefits:**
- Make small changes without passing the entire template
- Override specific fields while keeping the rest of the template intact
- Useful for testing different sequence patterns or static values
- Reduces request payload size

### Example 5: Python Client

```python
import requests

# Generate data using template names
response = requests.post('http://localhost:5000/api/generate', json={
    'base_template': 'ndc_asn_cas',
    'generation_template': 'ndc_asn_cas',
    'count': 5
})

if response.status_code == 200:
    result = response.json()
    print(f"Generated {result['count']} records")
    for record in result['data']:
        print(record)
else:
    print(f"Error: {response.json()}")
```

### Example 6: JavaScript/TypeScript Client

```typescript
async function generateData() {
  const response = await fetch('http://localhost:5000/api/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      base_template: 'ndc_asn_cas',
      generation_template: 'ndc_asn_cas',
      count: 3
    })
  });
  
  const result = await response.json();
  console.log(`Generated ${result.count} records`);
  return result.data;
}
```

## Error Responses

### Missing Required Field
```json
{
  "success": false,
  "error": "base_template is required"
}
```
Status: 400

### Template Not Found
```json
{
  "success": false,
  "error": "Base template 'invalid_template' not found in repository"
}
```
Status: 404

### Invalid Count
```json
{
  "success": false,
  "error": "count must be a positive integer"
}
```
Status: 400

### Count Too Large
```json
{
  "success": false,
  "error": "count cannot exceed 1000"
}
```
Status: 400

### Generation Error
```json
{
  "success": false,
  "error": "Error message here",
  "error_type": "ValueError"
}
```
Status: 500

## Request Limits

- Maximum `count` per request: 1000 records
- No rate limiting (consider adding for production)

## Template Updates & Server Lifecycle

### How Long Does the API Stay Active?

The API will stay active **until you stop it**:
- **Development mode**: Press `Ctrl+C` in the terminal to stop
- **Production mode**: Use process manager (systemd, PM2, etc.) to control lifecycle
- **Server crash**: API will stop if an unhandled error occurs

### Updating Templates

**Option 1: Reload Endpoint (Recommended)**
After updating template files, call the reload endpoint:
```bash
curl -X POST http://localhost:5000/api/templates/reload
```

**Option 2: Restart Server**
Stop the server (Ctrl+C) and restart it:
```bash
python api_service.py
```

**Note**: Templates are loaded into memory at startup. Changes to template files on disk won't be reflected until you either:
- Call the `/api/templates/reload` endpoint, OR
- Restart the server

### Best Practices

1. **Development**: Use the reload endpoint for quick iteration
2. **Production**: Restart the server after template updates for consistency
3. **Monitoring**: Check `/health` endpoint to verify server is running
4. **Version Control**: Track template changes in git for production deployments

## Template Sources

The API supports two ways to provide templates:

1. **Template Names**: Reference templates stored in the repository
   - Base templates: `templates/base_templates/<name>.json`
   - Generation templates: `templates/generation_templates/<name>.json`

2. **Inline Templates**: Pass full template objects in the request
   - Useful for one-off generations or testing
   - Templates are temporarily added to memory for the request

## Integration with Streamlit App

This API service uses the same template generation logic as the Streamlit app, ensuring consistency. You can:
- Use the Streamlit app for interactive template development
- Use the API for automated data generation in CI/CD pipelines
- Use the API for integration with other systems

## Production Considerations

1. **Use a Production WSGI Server**: Use gunicorn, uWSGI, or similar
2. **Add Authentication**: Implement API keys or OAuth
3. **Add Rate Limiting**: Prevent abuse
4. **Add Logging**: Track API usage
5. **Add Monitoring**: Health checks and metrics
6. **Add Caching**: Cache template loading if needed
7. **Add Validation**: More robust input validation

## Sequence Counter Management

The API supports persistent sequence counters to prevent duplicate keys across generation requests. Counters are stored in-memory and persist for the lifetime of the API server.

### Get Sequence Counters
```
GET /api/sequence-counters?template_name=<template_name>
```

Get all sequence counter values, optionally filtered by template name.

**Query Parameters:**
- `template_name` (optional): Filter counters for a specific template

**Response:**
```json
{
  "success": true,
  "counters": {
    "ndc_asn_cas::AsnId": 5,
    "ndc_asn_cas::Lpn.LpnId": 5,
    "ndc_asn_pcl::AsnId": 3
  },
  "template_name": "ndc_asn_cas"
}
```

### Get Template Sequence Counters
```
GET /api/sequence-counters/<template_name>
```

Get sequence counter values for a specific template.

**Response:**
```json
{
  "success": true,
  "template_name": "ndc_asn_cas",
  "counters": {
    "AsnId": 5,
    "Lpn.LpnId": 5
  }
}
```

### Reset Template Sequence Counters
```
DELETE /api/sequence-counters/<template_name>
```

Reset sequence counters for a specific template.

**Response:**
```json
{
  "success": true,
  "message": "Sequence counters reset for template 'ndc_asn_cas'"
}
```

### Reset All Sequence Counters
```
DELETE /api/sequence-counters
```

Reset all sequence counters across all templates.

**Response:**
```json
{
  "success": true,
  "message": "All sequence counters reset"
}
```

### Get Sequence Counter Enabled Status
```
GET /api/sequence-counters/enabled
```

Check whether persistent sequence counters are enabled (default: enabled for API).

**Response:**
```json
{
  "success": true,
  "enabled": true
}
```

### Enable/Disable Sequence Counters
```
POST /api/sequence-counters/enabled
```

Enable or disable persistent sequence counters.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Persistent sequence counters enabled"
}
```

**Usage Notes:**
- Counters are enabled by default in API mode
- Counters persist for the lifetime of the API server
- Counters reset when the server restarts
- Use `use_persistent_counters` parameter in generate requests (default: `true`)

## Limitations

### QueryContextFields
Templates using `QueryContextFields` are not supported in API mode because they require Streamlit session state for query data storage. 

**Workarounds:**
1. Use the Streamlit web app for templates with QueryContextFields
2. Remove QueryContextFields and use StaticFields or RandomFields instead
3. Pre-populate data using other template features

**Future Enhancement:** The API could be enhanced to accept query context data in the request body.

## Troubleshooting

**Issue**: Templates not found
- Check that template files exist in the correct directories
- Verify template names match file names (without .json extension)

**Issue**: Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version (3.8+ required)

**Issue**: Generation errors
- Check template format (must be valid JSON)
- Verify generation template has required sections
- Check error message for specific field issues

**Issue**: QueryContextFields error
- Templates with QueryContextFields cannot be used in API mode
- Use the Streamlit app or modify the template to remove QueryContextFields
