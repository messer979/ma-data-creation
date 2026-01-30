# Postman Setup Guide for Data Generation API

This guide will help you set up and test the Data Generation API in Postman.

## Prerequisites

1. **Start the API Service**
   ```bash
   cd ma-data-creation
   python api_service.py
   ```
   The API should be running on `http://localhost:5000`

2. **Install Postman** (if not already installed)
   - Download from: https://www.postman.com/downloads/

## Quick Setup (Import Collection)

### Step 1: Import the Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select the file: `Data_Generation_API.postman_collection.json`
4. Click **Import**

The collection will appear in your Postman workspace with all pre-configured requests.

### Step 2: Set Environment Variable

1. In Postman, click on **Environments** (left sidebar)
2. Click **+** to create a new environment
3. Name it: `Data Generation API - Local`
4. Add a variable:
   - **Variable**: `base_url`
   - **Initial Value**: `http://localhost:5000`
   - **Current Value**: `http://localhost:5000`
5. Click **Save**
6. Select this environment from the dropdown (top right)

### Step 3: Test the API

1. Open the **Data Generation API** collection
2. Click on **Health Check** request
3. Click **Send**
4. You should see a response with status 200 and template counts

## Manual Setup (Step by Step)

If you prefer to set up requests manually, follow these steps:

### 1. Create Environment

1. Click **Environments** → **+**
2. Name: `Data Generation API - Local`
3. Add variable:
   ```
   Variable: base_url
   Initial Value: http://localhost:5000
   Current Value: http://localhost:5000
   ```
4. Save and select the environment

### 2. Create Collection

1. Click **Collections** → **+**
2. Name: `Data Generation API`
3. Click **Create**

### 3. Add Requests

#### Request 1: Health Check

1. Click **+** to create new request
2. Name: `Health Check`
3. Method: **GET**
4. URL: `{{base_url}}/health`
5. Click **Save** → Select collection
6. Click **Send**

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "Data Generation API",
  "base_templates_loaded": 15,
  "generation_templates_loaded": 15
}
```

#### Request 2: List Templates

1. New request: `List Templates`
2. Method: **GET**
3. URL: `{{base_url}}/api/templates`
4. Save and Send

**Expected Response:**
```json
{
  "base_templates": ["ndc_asn_cas", "ndc_asn_pcl", ...],
  "generation_templates": ["ndc_asn_cas", "ndc_asn_pcl", ...]
}
```

#### Request 3: Generate Data (Template Names)

1. New request: `Generate - Template Names`
2. Method: **POST**
3. URL: `{{base_url}}/api/generate`
4. Go to **Headers** tab:
   - Key: `Content-Type`
   - Value: `application/json`
5. Go to **Body** tab:
   - Select **raw**
   - Select **JSON** from dropdown
   - Paste this:
   ```json
   {
       "base_template": "ndc_asn_cas",
       "generation_template": "ndc_asn_cas",
       "count": 3
   }
   ```
6. Save and Send

**Expected Response:**
```json
{
  "success": true,
  "data": [
    { ... generated record 1 ... },
    { ... generated record 2 ... },
    { ... generated record 3 ... }
  ],
  "count": 3,
  "metadata": {
    "base_template_source": "repository",
    "generation_template_source": "repository",
    "generated_at": "2026-01-27T10:30:00"
  }
}
```

#### Request 4: Generate Data (Partial Template)

Override specific sections of a repository template:

1. New request: `Generate - Partial Template`
2. Method: **POST**
3. URL: `{{base_url}}/api/generate`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
   ```json
   {
       "base_template": "ndc_asn_cas",
       "generation_template": {
           "template_name": "ndc_asn_cas",
           "SequenceFields": {
               "AsnId": "BGNDC{{dttm}}*"
           }
       },
       "count": 1
   }
   ```
6. Save and Send

**What happens:**
- Loads the full `ndc_asn_cas` generation template from repository
- Merges the provided `SequenceFields` section (replacing/adding `AsnId`)
- Uses all other sections from repository template (StaticFields, ArrayLengths, RandomFields, LinkedFields, etc.)

#### Request 5: Generate Data (Inline Templates)

1. New request: `Generate - Inline Templates`
2. Method: **POST**
3. URL: `{{base_url}}/api/generate`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
   ```json
   {
       "base_template": {
           "AsnId": null,
           "DestinationFacilityId": null,
           "EstimatedDeliveryDate": null,
           "Lpn": [
               {
                   "LpnId": null,
                   "EstimatedWeight": null,
                   "LpnDetail": [
                       {
                           "ItemId": null,
                           "ShippedQuantity": null
                       }
                   ]
               }
           ]
       },
       "generation_template": {
           "StaticFields": {
               "DestinationFacilityId": "TEST-001"
           },
           "SequenceFields": {
               "AsnId": "TEST{{dt}}"
           },
           "ArrayLengths": {
               "Lpn": 1,
               "Lpn.LpnDetail": 2
           },
           "RandomFields": {
               "Lpn.EstimatedWeight": "float(10,20,2)",
               "Lpn.LpnDetail.ItemId": "choiceOrder(ITEM001,ITEM002)",
               "Lpn.LpnDetail.ShippedQuantity": "int(5,10)"
           }
       },
       "count": 2,
       "template_name": "test_template"
   }
   ```
6. Save and Send

## Pre-configured Requests in Collection

The imported collection includes:

### Information Endpoints
- ✅ **Health Check** - API status
- ✅ **List Templates** - Available templates
- ✅ **Get Base Template** - Get specific base template
- ✅ **Get Generation Template** - Get specific generation template

### Generation Endpoints
- ✅ **Generate - Template Names** - Use repository templates
- ✅ **Generate - Inline Templates** - Pass full templates
- ✅ **Generate - Mixed** - Base from repo, generation inline
- ✅ **Generate - NDC ASN CAS (5 records)** - Quick test
- ✅ **Generate - NDC ASN PCL (3 records)** - Quick test

### Error Testing
- ✅ **Error - Missing base_template** - Test validation
- ✅ **Error - Invalid count** - Test validation
- ✅ **Error - Template not found** - Test error handling

## Testing Workflow

### 1. Verify API is Running
1. Run **Health Check** request
2. Should return status 200 with template counts

### 2. Explore Available Templates
1. Run **List Templates** request
2. Note available template names
3. Optionally run **Get Base Template** or **Get Generation Template** to see structure

### 3. Generate Test Data
1. Run **Generate - NDC ASN CAS (5 records)**
2. Verify response contains 5 records
3. Check that `AsnId` values are generated correctly

### 4. Test Inline Templates
1. Run **Generate - Inline Templates**
2. Verify custom template works
3. Check generated values match template rules

### 5. Test Error Handling
1. Run error test requests
2. Verify appropriate error messages
3. Check status codes (400 for validation errors, 404 for not found)

## Tips & Best Practices

### 1. Use Environment Variables
- Create different environments for different servers:
  - `Local`: `http://localhost:5000`
  - `Dev`: `http://dev-server:5000`
  - `Prod`: `http://prod-server:5000`

### 2. Save Responses as Examples
1. After sending a successful request
2. Click **Save Response** → **Save as Example**
3. Useful for documentation and testing

### 3. Use Pre-request Scripts
For dynamic values, add pre-request scripts:
```javascript
// Set current date in request body
pm.environment.set("current_date", new Date().toISOString().split('T')[0]);
```

### 4. Use Tests
Add test scripts to verify responses:
```javascript
// Test response structure
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Response has success field", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('success');
});

pm.test("Generated correct number of records", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.count).to.equal(5);
});
```

### 5. Organize with Folders
Create folders in collection:
- `Information` - Health check, list templates
- `Generation` - All generate requests
- `Testing` - Error test cases

## Troubleshooting

### Issue: "Could not get response"
- **Solution**: Make sure API is running (`python api_service.py`)
- Check the URL is correct: `http://localhost:5000`

### Issue: "Connection refused"
- **Solution**: Verify API is listening on port 5000
- Check firewall settings
- Try `http://127.0.0.1:5000` instead

### Issue: "Template not found"
- **Solution**: Verify template names match files in repository
- Run **List Templates** to see available templates
- Check template files exist in `templates/` directories

### Issue: "Invalid JSON"
- **Solution**: Verify request body is valid JSON
- Use Postman's JSON validator (auto-validates)
- Check for trailing commas or syntax errors

### Issue: "QueryContextFields not supported"
- **Solution**: This is expected - QueryContextFields require Streamlit
- Remove QueryContextFields from template or use Streamlit app

## Advanced: Collection Runner

Run all requests automatically:

1. Click on collection → **Run**
2. Select requests to run
3. Set iterations
4. Click **Run Data Generation API**
5. View results summary

## Export/Share Collection

1. Right-click collection → **Export**
2. Choose format (Collection v2.1 recommended)
3. Share with team or import elsewhere

## Next Steps

- Customize requests for your specific templates
- Add authentication if needed
- Set up automated testing with Newman (Postman CLI)
- Integrate with CI/CD pipelines
