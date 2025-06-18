import streamlit as st

@st.dialog("Data Creation Tool - Help Guide", width="large")
def guide_modal():
    """Comprehensive help guide for the Data Creation Tool"""
    
    # Create tabs for different help sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Overview", 
        "📋 Template Types",
        "🔧 Endpoint Config", 
        "📝 Generation Templates", 
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
        - **🗂️ Template Management**: Manage base and generation templates (session-only)
        - **🔧 Endpoint Config**: Configure API endpoints and authentication
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
            "DynamicFields": {"ItemId": "GEN_ITEM"},
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
          **🔢 DynamicFields:** Auto-incrementing values
        ```json
        "DynamicFields": {
            "ItemId": "CM_ITEM",
            "OrderId": "ORDER_{{dttm}}"
        }
        ```
        - `{{dttm}}` gets replaced with current date MMDD format
        - Fields increment automatically: `CM_ITEM_001`, `CM_ITEM_002`, etc.
        - **Array fields** increment per-record: Each ASN's lines start at 1
        - **Array length support**: Compatible with `ArrayLengths` specification
        
        **🎲 RandomFields:** Random values based on type
        ```json
        "RandomFields": [
            {
                "FieldName": "Quantity",
                "FieldType": "int(1,100)"
            },
            {
                "FieldName": "Price",
                "FieldType": "float(10.0,99.99,2)"
            },
            {
                "FieldName": "City",
                "FieldType": "choice(Atlanta,New York,Chicago)"
            },
            {
                "FieldName": "CreatedDate",
                "FieldType": "datetime(future)"
            }
        ]
        ```
        
        **🔗 LinkedFields:** Copy values between fields
        ```json
        "LinkedFields": {
            "ItemId": ["PrimaryBarCode", "Description"]
        }
        ```
          **📊 ArrayLengths:** Define array sizes for automatic expansion
        ```json
        "ArrayLengths": {
            "AsnLine": 2,
            "OrderLines": 3,
            "Lpn.LpnDetail": "int(1,5)"
        }
        ```
        - When defined, `AsnLine.ItemId` automatically applies to all array elements
        - No need to manually specify `AsnLine.0.ItemId`, `AsnLine.1.ItemId`
        - **Dynamic lengths**: Use `int(min,max)` for random array sizes
        - **Nested arrays**: Supports dot notation (e.g., `Lpn.LpnDetail`)
          ### Field Types:
        - `int(min,max)` - Random integer
        - `float(min,max,precision)` - Random decimal with specified precision
        - `float(min,max)` - Random decimal (default 2 decimals)
        - `float` - Random decimal 0-100 (default 2 decimals)
        - `string(length)` - Random alphanumeric string
        - `choice(opt1,opt2,opt3)` - Random selection from options
        - `choiceUnique(opt1,opt2,opt3)` - Unique selection within array siblings (auto-fallback when exhausted)
        - `datetime(now|future|past)` - Date/time generation
        - `boolean` - True/false values
        - `uuid` - UUID string generation
        - `email` - Random email addresses
          ### Nested Fields:
        Use dot notation for nested objects and arrays:
        - `Address.City` - City field in Address object
        - `AsnLine.ItemId` - ItemId in AsnLine array (auto-expands with ArrayLengths)
        - `Lpn.LpnDetail.QuantityUomId` - Multi-level nested arrays (up to 4 levels)
        
        ### 💾 Session-Only Storage:
        - **All generation templates** stored in browser session only
        - **Example templates** loaded automatically on startup
        - **Modifications lost** on page refresh (by design)
        - **Export before closing** to save your customizations
        """)
    
    with tab5:        
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
        
        **📋 Template Types Management:**
        - **Base Templates**: Structure definitions and default values
        - **Generation Templates**: Randomization and field generation rules
        - **Separate import/export** for each template type
        - **Quick overview** via sidebar expanders
        
        ### Features:
          **📝 Template Editing:**
        - **Visual editor** for both template types
        - **JSON syntax validation** with error checking
        - **Live preview** of template structure
        - **Session-only modifications** (temporary)
        - **Real-time template testing** with small data generation
          **📥📤 Session Import/Export:**
        - **Export templates** to JSON files for backup
        - **Import templates** from backup files (session-only)
        - **Bulk operations** for multiple templates
        - **Template validation** during import/export
        - **Filename prefixes** indicate session-only export
        - **Separate handling** for base and generation templates
        
        **🔍 Template Analysis:**
        - **Real-time overview** of loaded templates
        - **Field count and size** metrics
        - **Session status** indicators
        - **Template structure** validation
        
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

