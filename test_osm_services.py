#!/usr/bin/env python3
"""
Quick test script for OSM services endpoints.
Run after starting the backend to verify everything works.

Usage:
    python test_osm_services.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_poi_search():
    """Test POI search (Overpass)"""
    print("Testing POI search...")
    url = f"{BASE_URL}/osm/pois/search"
    payload = {
        "around": "40.4168,-3.7038,1000",
        "tags": {"amenity": "restaurant"},
        "limit": 5
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"✓ Found {len(data)} POIs")
        if data:
            print(f"  Example: {data[0].get('name', 'Unnamed')} at ({data[0]['lat']}, {data[0]['lon']})")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_route_calculate():
    """Test route calculation (OSRM)"""
    print("\nTesting route calculation...")
    url = f"{BASE_URL}/osm/route/calculate"
    payload = {
        "points": [[40.4168, -3.7038], [40.4165, -3.7026]],
        "profile": "driving"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        distance = data['distance']
        duration = data['duration']
        print(f"✓ Route calculated: {distance:.0f}m in {duration:.0f}s")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_route_optimize():
    """Test route optimization (OSRM /trip)"""
    print("\nTesting route optimization...")
    url = f"{BASE_URL}/osm/route/optimize"
    payload = {
        "points": [
            [40.4168, -3.7038],
            [40.4200, -3.7050],
            [40.4150, -3.7000]
        ],
        "profile": "driving",
        "roundtrip": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        distance = data['distance']
        duration = data['duration']
        waypoints = data.get('waypoints', [])
        order = [wp.get('waypoint_index') for wp in waypoints]
        print(f"✓ Route optimized: {distance:.0f}m in {duration:.0f}s")
        print(f"  Visit order: {order}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_geocode_forward():
    """Test forward geocoding (Nominatim)"""
    print("\nTesting forward geocoding...")
    url = f"{BASE_URL}/osm/geocode/forward"
    payload = {
        "query": "Plaza Mayor, Madrid",
        "limit": 3
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"✓ Found {len(data)} results")
        if data:
            print(f"  {data[0]['display_name']}")
            print(f"  Coords: ({data[0]['lat']}, {data[0]['lon']})")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_geocode_reverse():
    """Test reverse geocoding (Nominatim)"""
    print("\nTesting reverse geocoding...")
    url = f"{BASE_URL}/osm/geocode/reverse"
    payload = {
        "lat": 40.4168,
        "lon": -3.7038
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"✓ Address found:")
        print(f"  {data['display_name']}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("OSM Services Test Suite")
    print("=" * 60)
    print(f"Backend URL: {BASE_URL}")
    print()
    
    results = []
    results.append(("POI Search", test_poi_search()))
    results.append(("Route Calculate", test_route_calculate()))
    results.append(("Route Optimize", test_route_optimize()))
    results.append(("Forward Geocode", test_geocode_forward()))
    results.append(("Reverse Geocode", test_geocode_reverse()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
