# Inventory Transfer Testing Setup

This directory contains a complete testing environment for the inventory transfer UI that allows you to test the functionality without making real API calls.

## 🎯 Overview

The testing setup includes:
- **Dummy Server** (`dummy_server.py`) - Simulates Manhattan Active WM API endpoints
- **Test Transfer Module** (`test_inventory_transfer.py`) - HTTP-based inventory transfer using requests
- **UI Integration** - Modified Data Import page with test mode toggle
- **Test Scripts** - Automated testing and startup scripts

## 🚀 Quick Start

### Option 1: Automated Startup (Recommended)

**Windows:**
```bash
./start_test_env.bat
```

**Linux/Mac:**
```bash
chmod +x start_test_env.sh
./start_test_env.sh
```

### Option 2: Manual Startup

1. **Start the dummy server:**
   ```bash
   python dummy_server.py
   ```

2. **In a new terminal, start Streamlit:**
   ```bash
   streamlit run app.py
   ```

3. **Test the setup:**
   ```bash
   python test_setup.py
   ```

## 🧪 Using Test Mode

1. Open http://localhost:8501 in your browser
2. Navigate to **Data Import** page
3. Check the **🧪 Test Mode (Use Dummy Server)** checkbox
4. Configure your test settings:
   - Source zones: ZONE1, ZONE2, ZONE3, or STAGING
   - Target zone: Choose destination zone
   - Batch sizes: Use smaller values for testing (50/25)
5. Click **🚀 Start Transfer**
6. Monitor the real-time logs and progress

## 📊 Dummy Server Features

The dummy server simulates these endpoints:

- `POST /inventory/search` - Returns paginated inventory data by zone
- `POST /item/search` - Returns item details
- `POST /item/bulk-import` - Simulates item import
- `POST /item/sync` - Simulates item synchronization
- `POST /inventory/adjust` - Simulates inventory adjustments
- `GET /health` - Health check
- `GET /debug/requests` - View logged requests (debugging)

### Simulated Data

- **ZONE1**: ~1,250 inventory records
- **ZONE2**: ~890 inventory records  
- **ZONE3**: ~2,100 inventory records
- **STAGING**: ~450 inventory records

## 🔧 Configuration

### Test Mode Features

When test mode is enabled:
- Source/target URLs point to `http://localhost:5000`
- Predefined test zones available
- Smaller batch sizes for faster testing
- No real API credentials needed

### Dummy Server Behavior

- **Response Times**: Simulated delays (0.3-2.0 seconds)
- **Failure Simulation**: ~5% failure rate for large batches
- **Pagination**: Supports proper pagination with headers
- **Logging**: All requests logged to console and debug endpoint

## 📁 File Structure

```
├── dummy_server.py              # Mock API server
├── test_inventory_transfer.py   # HTTP-based transfer logic
├── test_setup.py               # Validation test script
├── start_test_env.bat          # Windows startup script
├── start_test_env.sh           # Linux/Mac startup script
├── pages/
│   └── data_import.py          # UI with test mode toggle
└── logs/                       # Runtime logs (created automatically)
    ├── dummy_server.log
    └── streamlit.log
```

## 🐛 Debugging

### Check Server Status
```bash
curl http://localhost:5000/health
```

### View Logged Requests
```bash
curl http://localhost:5000/debug/requests
```

### Clear Request Log
```bash
curl -X POST http://localhost:5000/debug/clear
```

### Manual API Testing

Test inventory search:
```bash
curl -X POST http://localhost:5000/inventory/search \
  -H "Content-Type: application/json" \
  -d '{"LocationQuery": {"Query": "Zone =ZONE1 and InventoryReservationTypeId=LOCATION"}, "Size": 10, "Page": 0}'
```

## 📝 Logs

- **Dummy Server**: `logs/dummy_server.log`
- **Streamlit App**: `logs/streamlit.log`
- **Transfer Logs**: Available for download from UI

## ⚠️ Important Notes

1. **Port Usage**: 
   - Dummy server: `localhost:5000`
   - Streamlit app: `localhost:8501`

2. **Test vs Production**:
   - Test mode uses HTTP requests to dummy server
   - Production mode uses pymawm library with real credentials

3. **Data Safety**:
   - Test mode makes no real API calls
   - All data is simulated and temporary

## 🎯 Testing Scenarios

### Basic Transfer Test
1. Enable test mode
2. Select ZONE1 as source
3. Select STAGING as target
4. Use default batch sizes
5. Run transfer and verify logs

### Large Data Test
1. Select ZONE3 (highest record count)
2. Use smaller batch sizes (25/10)
3. Monitor pagination and progress

### Multi-Zone Test
1. Run multiple transfers with different zones
2. Check debug endpoint for request history
3. Verify inventory distribution

## 🔄 Production Migration

When ready to use with real environments:
1. Uncheck test mode
2. Enter real environment credentials
3. Configure appropriate batch sizes
4. The same UI will use the production pymawm library

## 🆘 Troubleshooting

**"Cannot connect to dummy server"**
- Ensure dummy server is running on port 5000
- Check `logs/dummy_server.log` for errors
- Verify no other service is using port 5000

**"Import errors"**
- Run `pip install -r requirements.txt`
- Ensure Flask is installed

**"Streamlit not starting"**
- Check port 8501 is available
- Review `logs/streamlit.log` for errors
- Try different port: `streamlit run app.py --server.port 8502`
