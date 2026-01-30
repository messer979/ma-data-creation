"""
Simple test script for the Data Generation API
Run this after starting the API service to test it
"""

import requests
import json

API_BASE_URL = "http://localhost:5000"

def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_list_templates():
    """Test template listing"""
    print("Testing template list...")
    response = requests.get(f"{API_BASE_URL}/api/templates")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_generate_with_template_names():
    """Test generation using template names from repository"""
    print("Testing generation with template names...")
    payload = {
        "base_template": "ndc_asn_cas",
        "generation_template": "ndc_asn_cas",
        "count": 2
    }
    response = requests.post(f"{API_BASE_URL}/api/generate", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    if result.get('success'):
        print(f"✅ Generated {result['count']} records")
        print(f"First record AsnId: {result['data'][0].get('AsnId', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error')}")
    print()

def test_generate_with_inline_templates():
    """Test generation using inline templates"""
    print("Testing generation with inline templates...")
    payload = {
        "base_template": {
            "AsnId": None,
            "DestinationFacilityId": None,
            "EstimatedDeliveryDate": None,
            "Lpn": [
                {
                    "LpnId": None,
                    "EstimatedWeight": None,
                    "LpnDetail": [
                        {
                            "ItemId": None,
                            "ShippedQuantity": None
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
        "count": 1,
        "template_name": "test_template"
    }
    response = requests.post(f"{API_BASE_URL}/api/generate", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    if result.get('success'):
        print(f"✅ Generated {result['count']} records")
        print(f"Generated data: {json.dumps(result['data'], indent=2)}")
    else:
        print(f"❌ Error: {result.get('error')}")
    print()

def test_error_handling():
    """Test error handling"""
    print("Testing error handling...")
    
    # Missing required field
    print("  Testing missing base_template...")
    response = requests.post(f"{API_BASE_URL}/api/generate", json={"count": 1})
    print(f"    Status: {response.status_code}")
    print(f"    Error: {response.json().get('error')}")
    
    # Invalid count
    print("  Testing invalid count...")
    response = requests.post(f"{API_BASE_URL}/api/generate", json={
        "base_template": "ndc_asn_cas",
        "generation_template": "ndc_asn_cas",
        "count": -1
    })
    print(f"    Status: {response.status_code}")
    print(f"    Error: {response.json().get('error')}")
    
    # Template not found
    print("  Testing template not found...")
    response = requests.post(f"{API_BASE_URL}/api/generate", json={
        "base_template": "nonexistent_template",
        "generation_template": "ndc_asn_cas",
        "count": 1
    })
    print(f"    Status: {response.status_code}")
    print(f"    Error: {response.json().get('error')}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Data Generation API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health_check()
        test_list_templates()
        test_generate_with_template_names()
        test_generate_with_inline_templates()
        test_error_handling()
        
        print("=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure the API is running on http://localhost:5000")
        print("   Start the API with: python api_service.py")
    except Exception as e:
        print(f"❌ Error: {e}")
