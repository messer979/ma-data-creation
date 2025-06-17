"""
Dummy Web Server for Testing Inventory Transfer UI
Simulates API responses without making real calls to environments
"""

from flask import Flask, request, jsonify
import json
import time
import random
from datetime import datetime

app = Flask(__name__)

# Store received requests for debugging
received_requests = []

def log_request(endpoint, data):
    """Log received requests"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "data": data
    }
    received_requests.append(log_entry)
    print(f"[{log_entry['timestamp']}] {endpoint}: {json.dumps(data, indent=2)}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Dummy server is running"})

@app.route('/inventory/search', methods=['POST'])
def inventory_search():
    """Simulate inventory search endpoint"""
    data = request.get_json()
    log_request("POST /inventory/search", data)
    
    # Extract query parameters
    location_query = data.get('LocationQuery', {}).get('Query', '')
    size = data.get('Size', 10)
    page = data.get('Page', 0)
    
    # Extract zone from query (Zone =ZONE1 and InventoryReservationTypeId=LOCATION)
    zone = "ZONE1"  # Default
    if 'Zone =' in location_query:
        zone = location_query.split('Zone =')[1].split(' ')[0]
    
    # Simulate total count based on zone
    total_counts = {
        "ZONE1": 1250,
        "ZONE2": 890,
        "ZONE3": 2100,
        "STAGING": 450
    }
    total_count = total_counts.get(zone, 1000)
    
    # Generate dummy inventory data
    inventory_data = []
    start_idx = page * size
    
    for i in range(size):
        record_idx = start_idx + i
        if record_idx >= total_count:
            break
            
        inventory_data.append({
            "OnHand": random.randint(1, 500),
            "LocationId": f"{zone}-{record_idx:04d}",
            "ItemId": f"ITEM{random.randint(10000, 99999)}",
            "ReservationTypeId": "LOCATION",
            "Zone": zone
        })
    
    # Simulate processing delay
    time.sleep(0.5)
    
    response = {
        "header": {
            "totalCount": total_count,
            "pageSize": size,
            "currentPage": page
        },
        "data": inventory_data
    }
    
    return jsonify(response)

@app.route('/item/search', methods=['POST'])
def item_search():
    """Simulate item search endpoint"""
    data = request.get_json()
    log_request("POST /item/search", data)
    
    query = data.get('query', '')
    size = data.get('size', 50)
    
    # Extract item IDs from query (ItemId in (ITEM1,ITEM2,ITEM3))
    item_ids = []
    if 'ItemId in (' in query:
        items_part = query.split('ItemId in (')[1].split(')')[0]
        item_ids = [item.strip() for item in items_part.split(',')]
    
    # Generate dummy item data
    items_data = []
    for item_id in item_ids[:size]:
        items_data.append({
            "ItemId": item_id,
            "Description": f"Description for {item_id}",
            "ItemType": "STANDARD",
            "UOM": "EA",
            "Weight": random.uniform(0.1, 10.0),
            "Length": random.uniform(1, 50),
            "Width": random.uniform(1, 50),
            "Height": random.uniform(1, 50)
        })
    
    time.sleep(0.3)
    
    response = {
        "data": items_data
    }
    
    return jsonify(response)

@app.route('/item/bulk-import', methods=['POST'])
def item_bulk_import():
    """Simulate item bulk import endpoint"""
    data = request.get_json()
    log_request("POST /item/bulk-import", data)
    
    if isinstance(data, list):
        item_count = len(data)
    else:
        item_count = 1
    
    time.sleep(0.8)  # Simulate processing time
    
    response = {
        "status": "success",
        "imported_count": item_count,
        "failed_count": 0
    }
    
    return jsonify(response)

@app.route('/item/sync', methods=['POST'])
def item_sync():
    """Simulate item sync endpoint"""
    data = request.get_json()
    log_request("POST /item/sync", data)
    
    time.sleep(2.0)  # Simulate sync processing time
    
    response = {
        "status": "success",
        "message": "Item sync completed"
    }
    
    return jsonify(response)

@app.route('/inventory/adjust', methods=['POST'])
def inventory_adjust():
    """Simulate inventory adjustment endpoint"""
    data = request.get_json()
    log_request("POST /inventory/adjust", data)
    
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON"}), 400
    
    if isinstance(data, list):
        adjustment_count = len(data)
    else:
        adjustment_count = 1
    
    # Simulate some failures randomly
    failed_records = []
    success_count = adjustment_count
    
    if adjustment_count > 10:  # Only simulate failures for larger batches
        failure_rate = 0.05  # 5% failure rate
        failed_count = int(adjustment_count * failure_rate)
        success_count = adjustment_count - failed_count
        
        for i in range(failed_count):
            failed_records.append({
                "index": i,
                "error": f"Simulated failure for record {i}",
                "itemId": f"ITEM{random.randint(10000, 99999)}"
            })
    
    time.sleep(0.5)  # Simulate processing time
    
    response = {
        "data": {
            "SuccessfulRecords": success_count,
            "FailedRecords": failed_records
        },
        "status": "success" if not failed_records else "partial_success"
    }
    
    return jsonify(response), 200

@app.route('/debug/requests', methods=['GET'])
def get_debug_requests():
    """Debug endpoint to see all received requests"""
    return jsonify({
        "total_requests": len(received_requests),
        "requests": received_requests[-10:]  # Last 10 requests
    })

@app.route('/debug/clear', methods=['POST'])
def clear_debug_requests():
    """Clear debug request log"""
    global received_requests
    count = len(received_requests)
    received_requests = []
    return jsonify({"message": f"Cleared {count} logged requests"})

if __name__ == '__main__':
    print("Starting dummy server for inventory transfer testing...")
    print("Available endpoints:")
    print("  POST /inventory/search - Simulate inventory search")
    print("  POST /item/search - Simulate item search")
    print("  POST /item/bulk-import - Simulate item import")
    print("  POST /item/sync - Simulate item sync")
    print("  POST /inventory/adjust - Simulate inventory adjustments")
    print("  GET /debug/requests - View logged requests")
    print("  POST /debug/clear - Clear request log")
    print("  GET /health - Health check")
    print("\nServer running on http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    app.run(host='localhost', port=5000, debug=True)
