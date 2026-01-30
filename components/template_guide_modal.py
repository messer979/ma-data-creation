import streamlit as st

@st.dialog("Data Creation Tool - Help Guide", width="large")
def guide_modal():
    """Comprehensive help guide for the Data Creation Tool"""
    
    # Create tabs for different help sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Overview", 
        "📋 Template Types",
        "🔧 Endpoint Config", 
        "📝 Generation Templates",
        "🔍 Query Context",
        "🛠️ Template Manager"
    ])
    
    with tab1:
        st.markdown("""
        ## 🚀 Data Creation Tool Overview
        
        *This tool was built heavily relying on AI. Please report any issues or suggestions to cmesser.*
        
        ### Key Features:
        - **Generate structured test data** from JSON templates
        - **Session-only storage** - completely stateless server
        - **Send data to APIs** with configurable endpoints and authentication
        - **Customize data patterns** using generation templates
        - **Manage multiple templates** with bulk operations
        - **Configure API endpoints** per template type
        
        ### 🆕 Session-Only Architecture:
        - **All templates stored in browser session only**
        - **No server-side persistence** - server remains stateless
        - **Templates lost on page refresh** (by design)
        - **Export/import for permanent storage**
        - **Example templates loaded automatically** as starting points
        
        ### Basic Workflow:
        1. **Templates auto-load** as examples when you start
        2. **Select a data template** (ASN, PO, Items, etc.)
        3. **Configure generation parameters** (count, template settings)
        4. **Set up API endpoints** (optional)
        5. **Generate and send data** to your target system
        6. **Export templates** before closing to save your work
          ### Main Sections:
        - **📊 Data Generation**: Main interface for creating data
        - **🗂️ Template Management**: Bulk import/export for base and generation templates
        - **🔧 Endpoint Management**: Configure API endpoints and authentication
        - **📦 Inventory Import**: Direct inventory data transfer
        - **🧾 Order Import**: Direct order data transfer
        - **🔍 Query Context**: Execute SQL queries for realistic data generation
        - **📊 Generation History**: Track template usage and generation statistics
        """)
    
    with tab2:
        st.markdown("""
        ## 📋 Template Types Explained
        
        The system uses **two types of templates** that work together to generate data:
        
        ### 🏗️ Base Templates
        **What they are:**
        - **Structure definitions** for your data (JSON schema)
        - **Default field values** and data types
        - **Complete API payload structure**
        - **Read-only examples** loaded automatically on startup
        
        **Example - Item Base Template:**
        ```json
        {
            "ItemId": "ITEM01",
            "Description": "Sample Item",
            "Price": 10.99,
            "Active": true,
            "Categories": ["Electronics", "Gadgets"]
        }
        ```
        
        ### ⚙️ Generation Templates
        **What they are:**
        - **Instructions for randomizing** base template data
        - **Field-level customization** rules
        - **Array length controls** and patterns
        - **Dynamic value generation** logic
        
        **Example - Item Generation Template:**
        ```json
        {
            "StaticFields": {"Active": true},
            "SequenceFields": {"ItemId": "GEN_ITEM"},
            "RandomFields": [
                {"FieldName": "Price", "FieldType": "float(5.0,99.99,2)"}
            ],
            "LinkedFields": {"ItemId": ["Description"]}
        }
        ```
        
        ### 🔄 How They Work Together:
        1. **Base template** provides the structure and defaults
        2. **Generation template** defines what to randomize
        3. **System merges** both to create randomized records
        4. **Result**: Multiple unique records following the same structure
        
        ### 💾 Session Storage:
        - **Both template types** stored in browser session only
        - **Export before closing** to save your customizations
        - **Import to restore** previously exported templates
        
        ### 🔍 Where to Find Them:
        - **Template Management page**: View/edit both types
        - **Home page dropdown**: Lists generation templates for selection
        - **Sidebar expanders**: Quick overview of loaded templates
        """)
    
    with tab3:
        st.markdown("""
        ## 🔧 Endpoint Configuration
        
        The Endpoint Configuration section allows you to set up API endpoints for each template type.
        
        ### Configuration Options:
        
        **🌐 Global Settings:**
        - **Base URL**: The root URL for your API (e.g., `https://api.example.com`)
        - **Auth Token**: Authentication token for API requests
        - **Organization**: Default organization value
        - **Facility**: Default facility value
        
        **📡 Template-Specific Endpoints:**
        - **Endpoint URL**: Specific endpoint path for each template type
        - **Payload Wrapping**: Choose how data is packaged:
          - **XINT Mode**: Wraps data in `{"Payload": {...}}`
          - **Data Wrapper**: Wraps records in `{"data": [records]}`
          - **Raw Mode**: Sends data as direct array
        
        ### How to Configure:
        1. **Set Global Settings** in the sidebar
        2. **Configure specific endpoints** for each template type
        3. **Choose payload format** based on your API requirements
        4. **Test connections** using the preview functionality
        
        ### Authentication:
        - Set your auth token in the global configuration
        - Token is automatically included in all API requests
        - Supports Bearer token authentication
        """)
    
    with tab4:
        st.markdown("""
        ## 📝 Generation Templates
        
        Generation templates define how data should be generated for base templates. They control field values, randomization, and data patterns.
        
        ### Template Structure:
        
        **📌 StaticFields:** Fixed values for all records
        ```json
        "StaticFields": {
            "Status": "ACTIVE",
            "Version": 1,
            "IsEnabled": true
        }
        ```
          **🔢 SequenceFields:** Auto-incrementing values with persistent counters
        ```json
        "SequenceFields": {
            "AsnId": "BGNDCCAS{{dt}}*",
            "Lpn.LpnId": "{{AsnId}}*",
            "Lpn.LpnDetail.Extended.OriginalNDCLpnId": "substr({{Lpn.LpnId}},0,17)*"
        }
        ```
        **Features:**
        - `{{dt}}` gets replaced with current date (YYYYMMDD format)
        - `{{dttm}}` gets replaced with current datetime (YYYYMMDDHHMMSS format)
        - Fields increment automatically: `BGNDCCAS0127001`, `BGNDCCAS0127002`, etc.
        - **Underscore Control**: Append `*` to exclude underscore (e.g., `BGNDCCAS0127001` vs `BGNDCCAS0127_001`)
        - **Attribute References**: Use `{{FieldName}}` to reference other field values
        - **Substring Function**: Use `substr({{FieldName}},start,length)` to extract portions of values
        - **Persistent Counters**: When enabled, counters persist across generation requests
        - **Array fields**: Use dot notation directly (e.g., `Lpn.LpnId`) - no need to specify array indices
        - **Global Increment**: Sequence fields in arrays increment globally across all records
        
        **🎲 RandomFields:** Random values based on type (Key-Value Format)
        ```json
        "RandomFields": {
            "Quantity": "int(1,100)",
            "Price": "float(10.0,99.99,2)",
            "City": "choice(Atlanta,New York,Chicago)",
            "Status": "choiceUnique(PENDING,ACTIVE,COMPLETED)",
            "CreatedDate": "datetime(future)",
            "Weight": "float(5,50)",
            "IsActive": "boolean"
        }
        ```
        
        **Key Changes:**
        - Now uses **key:value map** format instead of array
        - Field name is the key, field type is the value
        - Cleaner, more concise syntax
        - Supports all nested field paths with dot notation
        
        **🔗 LinkedFields:** Copy values between fields
        ```json
        "LinkedFields": {
            "ItemId": ["PrimaryBarCode", "Description"]
        }
        ```
        
        **🔍 QueryContextFields:** Use SQL query results for realistic data
        ```json
        "QueryContextFields": {
            "facility_id": {
                "query": "facilities",
                "column": "facility_id",
                "mode": "random"
            },
            "calculated_quantity": {
                "query": "items",
                "column": "PACKS_QUANTITY",
                "mode": "match",
                "template_key": "item_id",
                "query_key": "ITEM_ID",
                "operation": "*(3,7)"
            }
        }
        ```
        
        **Query Context Modes:**
        - `random` - Random value from query column
        - `unique` - Random from unique values only
        - `sequential` - Deterministic selection
        - `match` - Lookup based on template/query key relationship
        
        **Mathematical Operations:**
        - `+10` - Add 10 to value
        - `*(3,7)` - Multiply by random number between 3-7
        - `-(1,5)` - Subtract random number between 1-5
        - `/2` - Divide by 2
        - `%100` - Modulo 100
        
          **📊 ArrayLengths:** Define array sizes for automatic expansion
        ```json
        "ArrayLengths": {
            "Lpn": 1,
            "Lpn.LpnDetail": "int(5,15)",
            "OrderLines": "choiceOrder(3,5,7)"
        }
        ```
        **Features:**
        - **Static Length**: Use integer (e.g., `1`, `10`) for fixed array sizes
        - **Variable Length**: Use `int(min,max)` for random array sizes between min and max
        - **Sequential Choice**: Use `choiceOrder(val1,val2,...)` to cycle through lengths across records
        - **Dot Notation**: Use dot notation (e.g., `Lpn.LpnDetail`) for nested arrays
        - **Auto-Expansion**: When defined, `Lpn.LpnDetail.ItemId` automatically applies to all array elements
        - **No Manual Indices**: No need to specify `Lpn.0.LpnId` or `Lpn.LpnDetail.0.ItemId` - use dot notation directly
          ### Field Types:
        - `int(min,max)` - Random integer between min and max
        - `int(length)` - Random integer with specific digit length (e.g., `int(5)` = 5-digit number)
        - `float(min,max,precision)` - Random decimal with specified precision
        - `float(min,max)` - Random decimal (default 2 decimals)
        - `float` - Random decimal 0-100 (default 2 decimals)
        - `string(length)` - Random alphanumeric string
        - `choice(opt1,opt2,opt3)` - Random selection from options
        - `choiceUnique(opt1,opt2,opt3)` - **Unique selection across all records** (no duplicates until exhausted, then auto-reuses)
        - `datetime(now|future|past)` - Date/time generation
        - `datetime(7)` - Date/time N days from now (positive = future, negative = past)
        - `boolean` - True/false values
        - `uuid` - UUID string generation
        - `email` - Random email addresses
        
        ### 🔒 Uniqueness Behavior:
        **`choiceUnique` tracks values across ALL records and arrays:**
        - First record uses first unique value
        - Second record uses second unique value
        - Once all choices exhausted, automatically reuses values
        - Example: `choiceUnique(A,B,C)` with 5 records → A, B, C, A, B
        - **Works for both simple fields and array fields**
        
        ### Query Context Integration:
        - Use **Query Context page** to execute SQL queries against target environment
        - Reference query results in `QueryContextFields` for realistic data generation
        - Supports mathematical operations on query values: `*(1,10)`, `+50`, etc.
        - Match mode enables lookups: find vendor for specific item, etc.
          ### Nested Fields:
        Use dot notation for nested objects and arrays:
        - `Address.City` - City field in Address object
        - `AsnLine.ItemId` - ItemId in AsnLine array (auto-expands with ArrayLengths)
        - `Lpn.LpnDetail.QuantityUomId` - Multi-level nested arrays (up to 4 levels)
        
        ### 🔢 Persistent Sequence Counters:
        - **Enable in Sidebar**: Toggle "Store Sequence Counter Values" to enable persistence
        - **View Counters**: Click "Sequence Values" button to see current counter values
        - **Reset Options**: Reset counters for specific templates or all templates
        - **Prevents Duplicates**: Counters continue incrementing across generation requests
        - **Session-Based**: Counters persist within your browser session
        - **Use Case**: Generate multiple ASN batches without duplicate LPN IDs
        
        **Example:**
        - Generate 3 ASNs with `Lpn.LpnId` starting at `BGNDCCAS0127001`
        - Generate 3 more ASNs - they continue from `BGNDCCAS0127004` (not reset to 001)
        - Prevents SQL duplicate key exceptions when importing multiple batches
        
        ### 📝 Template Format Notes:
        - **Dot Notation**: Use dot notation directly (e.g., `Lpn.LpnId`) - no need to specify array indices
        - **Nested Objects**: No need to specify nested object structures - arrays are handled automatically via `ArrayLengths`
        - **Partial Templates (API)**: In API mode, you can pass partial templates with `template_name` to override specific sections
        
        **API Partial Template Example:**
        ```json
        {
            "template_name": "ndc_asn_cas",
            "SequenceFields": {
                "AsnId": "BGNDC{{dttm}}*"
            }
        }
        ```
        This loads the full template from repository and merges only the provided sections.
        
        ### 💾 Session-Only Storage:
        - **All generation templates** stored in browser session only
        - **Example templates** loaded automatically on startup
        - **Modifications lost** on page refresh (by design)
        - **Export before closing** to save your customizations
        """)
    
    with tab5:
        st.markdown("""
        ## 🔍 Query Context Integration
        
        The Query Context feature allows you to execute SQL queries against your target environment and use the results to generate realistic test data.
        
        ### 🚀 Getting Started:
        
        **1. Execute Queries:**
        - Navigate to **🔍 Query Context** page
        - Connect to your target database/API
        - Execute SQL queries to fetch reference data
        - Name your queries for easy reference
        
        **2. Use in Templates:**
        - Reference query results in `QueryContextFields`
        - Generate data based on real system values
        - Create relationships between generated records
        
        ### 📊 Query Execution:
        
        **SQL Editor Features:**
        - **Syntax highlighting** and formatting
        - **Pretty print** functionality for readability
        - **Organization input** for API context
        - **Query naming** for template reference
        
        **Data Storage:**
        - **Session-only storage** - no server persistence
        - **DataFrame format** for easy manipulation
        - **Quick access** from generation templates
        - **Memory efficient** storage in session state
        
        ### 🔧 Template Integration:
        
        **QueryContextFields Structure:**
        ```json
        "QueryContextFields": {
            "facility_id": {
                "query": "facilities",
                "column": "facility_id", 
                "mode": "random"
            },
            "calculated_price": {
                "query": "items",
                "column": "base_price",
                "mode": "match",
                "template_key": "item_id",
                "query_key": "item_id",
                "operation": "*(1.1,1.5)"
            }
        }
        ```
        
        ### 🎯 Selection Modes:
        
        **`random`**: Random value from query column
        - Picks any random value from the specified column
        - Good for general reference data like facilities, vendors
        
        **`unique`**: Random from unique values only  
        - Ensures no duplicate values in generated data
        - Useful for fields that should be unique
        
        **`sequential`**: Deterministic selection
        - Uses consistent selection based on field name
        - Same field always gets same value for reproducibility
        
        **`match`**: Lookup based on relationships
        - Finds related data based on key matching
        - Requires `template_key` and `query_key` parameters
        - Example: Find vendor for specific item
        
        ### ⚙️ Mathematical Operations:
        
        Apply transformations to query values:
        
        **Basic Operations:**
        - `+10` - Add 10 to the value
        - `-5` - Subtract 5 from the value  
        - `*2` - Multiply by 2
        - `/3` - Divide by 3
        - `%100` - Modulo 100
        
        **Range Operations (NEW):**
        - `*(1,10)` - Multiply by random number between 1-10
        - `+(50,200)` - Add random number between 50-200
        - `-(1,5)` - Subtract random number between 1-5
        - `/(2,4)` - Divide by random number between 2-4
        
        ### 💡 Use Cases:
        
        **Reference Data Generation:**
        - Use real facility IDs, item codes, vendor numbers
        - Ensure generated data matches system constraints
        - Maintain referential integrity in test data
        
        **Realistic Calculations:**
        - Base prices on actual item costs with markup
        - Calculate quantities based on pack sizes
        - Generate dates relative to existing schedules
        
        **Data Relationships:**
        - Link orders to valid customers
        - Assign items to correct vendors
        - Match facilities with appropriate locations
        
        ### ⚠️ Important Notes:
        
        - **Query results stored in session only**
        - **Lost on page refresh** - re-execute as needed
        - **No server-side caching** - completely stateless
        - **Failed queries ignored** - templates continue with other fields
        - **Performance**: Large result sets may slow generation
        
        ### 🔍 Best Practices:
        
        - **Name queries clearly** for easy template reference
        - **Limit result sets** to essential data only
        - **Test queries first** before using in templates
        - **Use match mode** for creating realistic relationships
        - **Apply operations** to add variability to real data
        """)
    
    with tab6:        
        st.markdown("""
        ## 🛠️ Template Manager (Session-Only)
        
        The Template Manager provides tools for managing, editing, and organizing your templates in session memory only.
        
        ### 🆕 Session-Only Features:
        
        **💾 Session Storage:**
        - **All templates** stored in browser session only
        - **No server-side files** created or modified
        - **Server remains stateless** - no user data persistence
        - **Templates lost on refresh** (by design for privacy)
        - **Export/import** for permanent storage
        
        **📋 Bulk Import/Export:**
        - **Single export button** for all base AND generation templates
        - **Single import button** to restore complete configuration
        - **Comprehensive JSON format** includes metadata and counts
        - **Conflict detection** shows new vs. overwrite status
        - **Overwrite control** via checkbox during import
        
        ### Features:
          **📝 Template Editing:**
        - **Visual editor** for both template types
        - **JSON syntax validation** with error checking
        - **Live preview** of template structure
        - **Session-only modifications** (temporary)
        - **Create, edit, delete** templates in session
          **📥📤 Unified Import/Export:**
        - **Single file** contains all templates (base + generation)
        - **Environment settings** also included in export
        - **Endpoint configurations** preserved
        - **Import preview** shows what will be added/updated
        - **Detailed results** after import (imported, skipped, errors)
        
        **💾 Full Config Export (Sidebar):**
        - **One-click export** of complete RAD configuration
        - **Includes**: endpoints, base templates, generation templates, environment settings
        - **Status tracking**: Shows "Updated at HH:MM" or "Saved"
        - **Automatic tracking**: Labels update when config changes detected
        
        **🔍 Template Analysis:**
        - **Real-time overview** of loaded templates
        - **Field count and size** metrics
        - **Session status** indicators
        - **Template structure** validation
        - **Side-by-side comparison** of base and generation templates
        
        ### How to Use:
        
        **Managing Session Templates:**
        1. Navigate to **🗂️ Template Management** page
        2. View **template overview** in sidebar expanders
        3. **Edit templates** in the Template Editor tab
        4. **Export before closing** to save your work
        
        **Working with Session Data:**
        1. **Example templates** load automatically on startup
        2. **Modify templates** as needed (session-only)
        3. **Test with small batches** before large generation
        4. **Export customizations** before page refresh
        5. **Import exported files** to restore templates
        
        **Best Practices:**
        - **Export frequently** - templates are lost on refresh
        - **Test modifications** with small record counts first
        - **Use consistent naming** across template types
        - **Check template counts** in sidebar expanders
        - **Validate imports** after restoring templates
        
        ### ⚠️ Important Session Warnings:
        - **Templates lost on page refresh/browser close**
        - **No automatic saving** to server
        - **Export is your only permanent storage**
        - **Import only loads to current session**
        - **Server remains completely stateless**
          ### Template Validation:
        The manager automatically checks for:
        - **Valid JSON syntax** in both template types
        - **Required field structures** for generation templates
        - **Field type formatting** and syntax
        - **ArrayLengths consistency** with base templates
        - **LinkedFields dependencies** and references        - **Template structure validation** during imports
        
        ### 📊 Data Preview & Download:
        - **JSON and CSV export** of generated data
        - **Code view toggle** for better JSON inspection
        - **Batch data preview** (first 3 records shown)
        - **Real-time payload preview** before API sending
        """)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("💡 **Tip**: Use the different tabs above to learn about specific features.")
        st.markdown("🔄 **Testing**: Generate small batches first to test your configuration.")
    with col2:
        st.markdown("⚠️ **Remember**: Export templates before closing - session-only storage!")
        st.markdown("📋 **Quick Check**: Use sidebar expanders to see loaded template counts.")
        st.markdown("🔍 **Testing**: Try small record counts first to validate templates.")

