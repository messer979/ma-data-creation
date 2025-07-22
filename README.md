# 🚀 Data Creation Tool

A powerful Streamlit-based web application for generating massive amounts of test data using JSON templates and sending them via API calls. Built with a modular architecture for maintainability and extensibility.

## ✨ Features

- **Template-Based Data Generation**: Generate test data using customizable JSON templates
- **Query Context Integration**: Execute SQL queries against target environments to gather real data for context-aware generation
- **Configurable API Endpoints**: Template-specific endpoint configuration with payload wrapping
- **Batch Processing**: Send data in configurable batch sizes to prevent API overload
- **Real-time Payload Preview**: See how your data will be structured before sending
- **Flexible Payload Wrapping**: Support for XINT envelopes, data wrappers, and raw arrays
- **Modern UI**: Clean, responsive interface with dark/light theme support
- **Configuration Management**: Import/export configurations, global settings management

## 🏗️ Architecture

### Modular Design
- **`app.py`**: Main Streamlit application entry point
- **`ui_components.py`**: Reusable UI components and rendering logic
- **`data_operations.py`**: Data generation and processing logic
- **`api_operations.py`**: API communication and batch processing
- **`config_manager.py`**: Configuration persistence and management
- **`endpoint_config_ui.py`**: Endpoint configuration interface
- **`data_generator.py`**: Core data generation engine

### Key Components
- **Template Engine**: JSON-based templates with variable substitution
- **Configuration System**: Session-based configuration with import/export
- **Payload Wrapping**: Configurable data envelope structures
- **Batch Processing**: Efficient API communication with rate limiting

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd data-creation-app
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run app.py
   ```

4. **Access the application**
   Open your browser to `http://localhost:8501`

## 📋 Usage Guide

### Basic Workflow

1. **Configure Global Settings**
   - Set base URL for your API environment
   - Configure authentication token
   - Set organization and facility values

2. **Select Data Template**
   - Choose from available data types (ASN, PO, Items, etc.)
   - Each template defines the structure of generated data

3. **Configure Template-Specific Endpoints**
   - Set endpoint URL for each data type
   - Configure payload wrapping options:
     - **XINT Mode**: Wraps data in `{"Payload": ...}` envelope
     - **Data Wrapper**: Wraps records in `{"data": [records]}`
     - **Raw Mode**: Sends data as direct array

4. **Generate Data**
   - Specify number of records to generate
   - Choose whether to send to API or just preview
   - Configure batch size for API calls

### Payload Wrapping Options

| Type | Data Wrapper | Result Structure |
|------|--------------|------------------|
| `none` | `false` | `[records]` |
| `none` | `true` | `{"data": [records]}` |
| `xint` | `false` | `{"Payload": [records]}` |
| `xint` | `true` | `{"Payload": {"data": [records]}}` |

## 🛠️ Configuration

### Template Configuration
Templates are stored in the `templates/` directory as JSON files. Each template defines:
- Field names and types
- Data generation rules
- Validation constraints

### Endpoint Configuration
Endpoint configurations support:
- Custom URLs per template type
- Payload wrapping preferences
- Authentication headers
- Batch processing settings

### Configuration Files
- **`configuration.json`**: Default system configuration
- **`user_config.json`**: User-specific overrides (gitignored)

## 🔍 Query Context Integration

The Query Context feature allows you to execute SQL queries against your target environment to gather real data for context-aware template generation. This enables creating test data that references actual entities in your system.

### How It Works

1. **Execute Queries**: Run SQL queries against your target database via API
2. **Store Results**: Query results are stored as pandas DataFrames in session state
3. **Use in Templates**: Reference query results in your generation templates using `QueryContextFields`

### Setting Up Query Context

1. **Configure Base URL**: Set your target environment's base URL in the sidebar
2. **Navigate to Query Context**: Go to the "Query Context" page
3. **Execute Queries**: Enter SQL queries to gather reference data

#### Example Query
```sql
SELECT facility_id, facility_name, status 
FROM facilities 
WHERE status = 'ACTIVE' 
LIMIT 100
```

### Using Query Results in Templates

Add `QueryContextFields` to your generation templates to use query results:

```json
{
  "QueryContextFields": {
    "facility_id": {
      "query": "facilities",
      "column": "facility_id", 
      "mode": "random"
    },
    "item_id": {
      "query": "items",
      "column": "item_id",
      "mode": "unique"
    },
    "OriginalOrderLine.OrderedQuantity": {
      "query": "items",
      "column": "PACKS_QUANTITY",
      "mode": "match",
      "template_key": "OriginalOrderLine.ItemId",
      "query_key": "ITEM_ID",
      "operation": "*5"
    }
  }
}
```

#### Query Modes
- **`random`**: Select random values from the column
- **`unique`**: Select from unique values only
- **`sequential`**: Select values in a deterministic sequence
- **`match`**: Lookup a specific row where template_key matches query_key, then use the column value from that row

#### Mathematical Operations
Add an `operation` field to perform calculations on retrieved values:
- **`*5`**: Multiply by 5
- **`*(1,5)`**: Multiply by random integer between 1 and 5
- **`+10`**: Add 10
- **`+(5,15)`**: Add random number between 5 and 15
- **`-3`**: Subtract 3  
- **`-(1,10)`**: Subtract random number between 1 and 10
- **`/2`**: Divide by 2
- **`/(2,5)`**: Divide by random number between 2 and 5
- **`%100`**: Modulo 100
- **`%(10,50)`**: Modulo by random number between 10 and 50
- **`^2`** or **`**2`**: Power of 2
- **`^(2,4)`** or **`**(2,4)`**: Power of random number between 2 and 4

Example: Multiply pack quantity by random value between 3 and 7:
```json
"OriginalOrderLine.OrderedQuantity": {
  "query": "items",
  "column": "PACKS_QUANTITY", 
  "mode": "match",
  "template_key": "OriginalOrderLine.ItemId",
  "query_key": "ITEM_ID",
  "operation": "*(3,7)"
}
```

### Benefits

- **Data Consistency**: Generate data using real facility IDs, item codes, etc.
- **Realistic Testing**: Create test scenarios with actual system constraints
- **Reference Integrity**: Ensure generated data references valid entities
- **Context Awareness**: Generate data that makes sense within your system's current state

### Query Context API

The feature assumes your target environment has a query endpoint at `/api/query` that accepts:
```json
{
  "query": "SELECT * FROM table",
  "format": "json"
}
```

Adjust the API endpoint structure in `pages/query_context.py` to match your system's API.

## 🧪 Testing

The project includes comprehensive tests:

```bash
# Run all tests
python -m pytest testing/

# Run specific test files
python testing/test_payload_wrapping.py
python testing/test_ui_config_integration.py
python testing/test_end_to_end.py
```

## 📁 Project Structure

```
data-creation-app/
├── app.py                     # Main application entry point
├── config_manager.py          # Configuration management
├── data_generator.py          # Core data generation
├── ui_components.py           # UI component library
├── endpoint_config_ui.py      # Endpoint configuration UI
├── api_operations.py          # API communication
├── data_operations.py         # Data processing logic
├── requirements.txt           # Python dependencies
├── configuration.json         # Default configuration
├── templates/                 # Data generation templates
│   ├── asn_item_level.json
│   ├── po.json
│   └── ...
├── generation_templates/      # Template generation rules
├── testing/                   # Test suite
└── archive/                   # Archived/backup files
```

## 🔧 Development

### Adding New Templates
1. Create JSON template in `templates/` directory
2. Add generation rules in `generation_templates/`
3. Configure endpoint in the UI or `configuration.json`

### Extending Functionality
- **New UI Components**: Add to `ui_components.py`
- **API Integrations**: Extend `api_operations.py`
- **Data Processing**: Modify `data_operations.py`
- **Configuration Options**: Update `config_manager.py`

## 📝 Recent Updates

### Endpoint Configuration Enhancement
- Added UI controls for payload type selection
- Implemented data wrapper toggle functionality
- Real-time payload structure preview
- Enhanced configuration validation

### Architecture Improvements
- Simplified configuration management (removed local storage dependency)
- Modular UI component structure
- Improved error handling and validation
- Enhanced test coverage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with Streamlit • Modular Architecture • Template-Specific Endpoints**
