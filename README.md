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

### Template System

The data creation tool uses a two-template system:

1. **Base Templates** (`templates/base_templates/`): Define the structure and schema of your data
2. **Generation Templates** (`templates/generation_templates/`): Define rules for populating base templates with dynamic data

### Base Templates

Base templates are JSON files that define the structure of your data. They contain:
- Field names and types
- Nested object structures
- Array definitions
- All values are typically set to `null` as placeholders

Example base template structure:
```json
{
  "AsnId": null,
  "DestinationFacilityId": null,
  "Lpn": [
    {
      "LpnId": null,
      "LpnDetail": [
        {
          "ItemId": null,
          "ShippedQuantity": null
        }
      ]
    }
  ]
}
```

### Generation Templates

Generation templates define how to populate base templates with dynamic data. They support the following sections:

#### 1. StaticFields

Fields that always have the same value across all generated records.

```json
{
  "StaticFields": {
    "DestinationFacilityId": "MA-038",
    "OriginFacilityId": "DC0087",
    "Lpn.LpnDetail.QuantityUomId": "UNIT"
  }
}
```

**Note**: Use dot notation (e.g., `Lpn.LpnDetail.ItemId`) to reference nested fields directly. No need to specify array indices or nested object structures - the system handles arrays automatically based on `ArrayLengths` configuration.

**Complete Generation Template Example:**
```json
{
  "StaticFields": {
    "AsnLevelId": "LPN",
    "DestinationFacilityId": "MA-038",
    "OriginFacilityId": "DC0087",
    "Lpn.Extended.CrossDockType": "CAS"
  },
  "SequenceFields": {
    "AsnId": "BGNDCCAS{{dt}}",        // With underscore: BGNDCCAS0127_001
    "Lpn.LpnId": "{{AsnId}}*"          // No underscore, references AsnId: BGNDCCAS0127001
  },
  "ArrayLengths": {
    "Lpn": 1,                          // Static: always 1
    "Lpn.LpnDetail": "int(5,15)"       // Variable: random between 5-15
  },
  "RandomFields": {
    "EstimatedDeliveryDate": "date(now)",
    "Lpn.EstimatedWeight": "float(250,600,2)",
    "Lpn.LpnDetail.ItemId": "choiceOrder(10000305,10000305,10000102)"
  },
  "QueryContextFields": {
    "Lpn.LpnDetail.StandardPackQuantity": {
      "query": "items",
      "column": "STANDARD_PACK_QTY",
      "mode": "match",
      "template_key": "Lpn.LpnDetail.ItemId",
      "query_key": "ITEM_ID"
    }
  },
  "LinkedFields": {
    "AsnId": [
      "Lpn.AsnId",
      "Lpn.LpnDetail.Extended.ShipmentNumber"
    ],
    "Lpn.LpnDetail.ShippedQuantity": [
      "Lpn.LpnDetail.StandardPackQuantity"
    ]
  }
}
```

#### 2. SequenceFields

Fields that increment sequentially. Supports date/time formatting, attribute references, substring extraction, and persistent counters across generation requests.

**Basic Syntax:**
```json
{
  "SequenceFields": {
    "AsnId": "BGNDCCAS{{dt}}*",
    "Lpn.LpnId": "{{AsnId}}*",
    "Lpn.LpnDetail.Extended.OriginalNDCLpnId": "substr({{Lpn.LpnId}},0,17)*"
  }
}
```

**Features:**
- **Date/Time Formatting**: Use `{{dt}}` for date (YYYYMMDD) or `{{dttm}}` for datetime
- **Underscore Control**: Append `*` to exclude underscore before sequence number
  - `"AsnId": "BGNDCCAS{{dt}}"` → `BGNDCCAS0127_001` (with underscore)
  - `"AsnId": "BGNDCCAS{{dt}}*"` → `BGNDCCAS0127001` (no underscore)
- **Attribute References**: Use `{{FieldName}}` to reference other field values
  - `"Lpn.LpnId": "{{AsnId}}*"` → Concatenates AsnId value with sequence number
- **Substring Function**: Use `substr({{FieldName}},start,length)` to extract portions of attribute values
  - `"OriginalNDCLpnId": "substr({{Lpn.LpnId}},0,17)*"` → First 17 characters of LpnId + sequence
- **Persistent Counters**: Sequence counters persist across generation requests (when enabled)
  - Counters continue incrementing across multiple data generation calls
  - Prevents duplicate key errors when generating multiple batches
  - Enable via "Store Sequence Counter Values" toggle in sidebar

**Examples:**
```json
{
  "SequenceFields": {
    "AsnId": "BGNDCCAS{{dt}}*",                                    // BGNDCCAS0127001, BGNDCCAS0127002...
    "Lpn.LpnId": "{{AsnId}}*",                                     // Uses AsnId + sequence: BGNDCCAS0127001, BGNDCCAS0127002...
    "Lpn.LpnDetail.Extended.OriginalNDCLpnId": "substr({{Lpn.LpnId}},0,17)*",  // First 17 chars + sequence
    "OrderNumber": "ORD{{dttm}}",                                  // ORD20260127143000_001, ORD20260127143001_002...
  }
}
```

**Important Notes:**
- **Dot Notation**: Use dot notation (e.g., `Lpn.LpnId`) to reference nested fields directly - no need to specify array indices
- **Array Fields**: Sequence fields in arrays increment globally across all records, ensuring uniqueness
- **Counter Persistence**: When enabled, counters persist across generation requests within your session
- **Counter Reset**: Use the "Sequence Values" button in sidebar to view and reset counters

#### 3. ArrayLengths

Defines the number of elements in arrays. Supports static integers or variable lengths.

**Static Length:**
```json
{
  "ArrayLengths": {
    "Lpn": 1,
    "Lpn.LpnDetail": 10
  }
}
```

**Variable Length:**
```json
{
  "ArrayLengths": {
    "Lpn": 1,
    "Lpn.LpnDetail": "int(5,15)",                    // Random length between 5-15
    "OrderLines": "choiceOrder(3,5,7)"                // Cycles: 3, 5, 7, 3, 5, 7...
  }
}
```

**Supported Formats:**
- **Static**: `5` (always 5 elements)
- **Random Range**: `int(min,max)` (random length between min and max)
- **Sequential Choice**: `choiceOrder(val1,val2,val3)` (cycles through values across all records)

#### 4. RandomFields

Fields that generate random values based on specified types.

```json
{
  "RandomFields": {
    "EstimatedDeliveryDate": "date(now)",
    "Lpn.EstimatedWeight": "float(250,600,2)",
    "Lpn.Volume": "float(1100,1900,3)",
    "Lpn.LpnDetail.ItemId": "choiceOrder(10000305,10000305,10000102)",
    "Lpn.LpnDetail.ShippedQuantity": "int(2,16)"
  }
}
```

**Supported Types:**
- **`int(min,max)`**: Random integer between min and max
- **`float(min,max,precision)`**: Random float between min and max with specified decimal precision
- **`date(now)`**: Current date/time
- **`choiceOrder(val1,val2,...)`**: Cycles through values sequentially
- **`choiceUnique(val1,val2,...)`**: Random selection without repetition until all values used

#### 5. LinkedFields

Fields whose values are copied from other fields in the same record.

```json
{
  "LinkedFields": {
    "AsnId": [
      "Lpn.AsnId",
      "Lpn.LpnDetail.Extended.ShipmentNumber",
      "Lpn.LpnDetail.Extended.VendorASNNbr"
    ],
    "Lpn.LpnDetail.ShippedQuantity": [
      "Lpn.LpnDetail.StandardPackQuantity",
      "Lpn.LpnDetail.Extended.InnerPackQuantity"
    ]
  }
}
```

The source field value is copied to all target fields listed in the array.

#### 6. QueryContextFields

Fields populated from query results (SQL queries or CSV files). See [Query Context Integration](#-query-context-integration) section for details.

**CSV Input Support:**
You can now load CSV files as query results instead of executing SQL queries. This enables:
- Manual item data profiles
- Pre-defined reference data
- Offline template generation

To load a CSV file, use the Query Context page to upload your CSV, then reference it in your template:

```json
{
  "QueryContextFields": {
    "Lpn.LpnDetail.ItemId": {
      "query": "item_profiles",  // Name of your CSV query
      "column": "ItemId",
      "mode": "random"
    }
  }
}
```

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

The Query Context feature allows you to gather real data for context-aware template generation. You can execute SQL queries against your target environment via API, or load CSV files with pre-defined data profiles.

### How It Works

1. **Load Data**: Execute SQL queries via API or upload CSV files
2. **Store Results**: Query results are stored as pandas DataFrames in session state
3. **Use in Templates**: Reference query results in your generation templates using `QueryContextFields`

### Setting Up Query Context

#### Option 1: SQL Queries (API-based)

1. **Configure Base URL**: Set your target environment's base URL in the sidebar
2. **Navigate to Query Context**: Go to the "Query Context" page
3. **Execute Queries**: Enter SQL queries to gather reference data

#### Option 2: CSV Files (Manual Profiles)

1. **Navigate to Query Context**: Go to the "Query Context" page
2. **Upload CSV**: Upload a CSV file with your data profiles
3. **Name Your Query**: Assign a name to reference in templates
4. **Use in Templates**: Reference the CSV data using the query name

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

### CSV Input Support

You can now load CSV files as query results instead of executing SQL queries. This enables:
- **Manual Item Data Profiles**: Pre-define item characteristics and attributes
- **Offline Template Generation**: Create data without API connectivity
- **Custom Reference Data**: Use any CSV data structure you need

**CSV Format Example:**
```csv
ITEM_ID,ITEM_DESCRIPTION,STANDARD_PACK_QTY,INNER_PACK_QTY,VENDOR_ID
10000305,Item Description 1,24,6,DC0087
10000102,Item Description 2,12,12,DC0087
```

**Using CSV in Templates:**
```json
{
  "QueryContextFields": {
    "Lpn.LpnDetail.ItemId": {
      "query": "item_profiles",  // Name of your CSV query
      "column": "ITEM_ID",
      "mode": "random"
    },
    "Lpn.LpnDetail.StandardPackQuantity": {
      "query": "item_profiles",
      "column": "STANDARD_PACK_QTY",
      "mode": "match",
      "template_key": "Lpn.LpnDetail.ItemId",
      "query_key": "ITEM_ID"
    }
  }
}
```

### Benefits

- **Data Consistency**: Generate data using real facility IDs, item codes, etc.
- **Realistic Testing**: Create test scenarios with actual system constraints
- **Reference Integrity**: Ensure generated data references valid entities
- **Context Awareness**: Generate data that makes sense within your system's current state
- **Flexible Data Sources**: Use SQL queries or CSV files based on your needs

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

### Generation Template Enhancements (Latest)

#### 1. Sequence Field Underscore Control
- Append `*` to sequence field templates to exclude underscore before sequence number
- Example: `"AsnId": "BGNDCCAS{{dt}}*"` → `BGNDCCAS0127001` (no underscore)

#### 2. Variable ArrayLengths
- Support for dynamic array lengths using `int(min,max)` for random ranges
- Support for `choiceOrder(val1,val2,...)` to cycle through lengths across records
- Example: `"Lpn.LpnDetail": "int(5,15)"` generates arrays with 5-15 elements

#### 3. Attribute Value References
- Reference other field values using `{{FieldName}}` syntax
- Enables field concatenation and cross-field dependencies
- Example: `"Lpn.LpnId": "{{AsnId}}*"` creates LPN IDs based on ASN ID

#### 4. Substring Function
- Extract portions of attribute values using `substr({{FieldName}},start,length)`
- Useful for creating derived fields from existing values
- Example: `"OriginalNDCLpnId": "substr({{Lpn.LpnId}},0,17)*"` extracts first 17 characters

#### 5. Persistent Sequence Counters
- Sequence counters persist across generation requests (when enabled)
- Prevents duplicate key errors when generating multiple batches
- Counters continue incrementing across all generation calls within a session
- Enable via "Store Sequence Counter Values" toggle in sidebar
- View and reset counters via "Sequence Values" button

#### 6. CSV Input for QueryContext
- Load CSV files as query results instead of requiring API execution
- Enables manual item data profiles and offline template generation
- Upload CSV files through the Query Context page

#### 7. Simplified Template Format
- **No need to specify nested object structures** - use dot notation directly
- Example: `"Lpn.LpnId"` instead of `"Lpn": {"0": {"LpnId": "..."}}`
- Works with arrays automatically via `ArrayLengths` configuration

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
