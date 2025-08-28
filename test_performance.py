#!/usr/bin/env python3
"""
Simple test script to verify the optimized FastAPI application performance
This script tests basic endpoints and measures response times
"""

import asyncio
import time
import sys
from typing import List
import httpx


async def test_endpoint(client: httpx.AsyncClient, endpoint: str, method: str = "GET", json_data=None) -> dict:
    """Test a single endpoint and measure response time"""
    start_time = time.time()
    try:
        if method.upper() == "GET":
            response = await client.get(endpoint)
        elif method.upper() == "POST":
            response = await client.post(endpoint, json=json_data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "response_time_ms": round(response_time, 2),
            "success": response.status_code < 400
        }
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": None,
            "response_time_ms": round(response_time, 2),
            "success": False,
            "error": str(e)
        }


async def run_performance_tests(base_url: str = "http://localhost:8000") -> List[dict]:
    """Run performance tests on key endpoints"""
    
    # Test endpoints
    test_cases = [
        {"endpoint": "/test", "method": "POST"},
        {"endpoint": "/api/requests", "method": "GET"},
        {"endpoint": "/api/cleanup/status", "method": "GET"},
        {"endpoint": "/api/history/stats", "method": "GET"},
        # Add more endpoints as needed
    ]
    
    results = []
    
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),  # 30 second timeout
        limits=httpx.Limits(max_connections=10)
    ) as client:
        
        print(f"🧪 Testing FastAPI application at {base_url}")
        print("=" * 60)
        
        for test_case in test_cases:
            print(f"Testing {test_case['method']} {test_case['endpoint']}...", end=" ")
            
            result = await test_endpoint(
                client, 
                f"{base_url}{test_case['endpoint']}", 
                test_case['method'],
                test_case.get('json_data')
            )
            
            results.append(result)
            
            if result['success']:
                print(f"✅ {result['response_time_ms']}ms")
            else:
                print(f"❌ {result.get('error', 'HTTP ' + str(result['status_code']))}")
        
        print("=" * 60)
        
        # Calculate summary stats
        successful_tests = [r for r in results if r['success']]
        if successful_tests:
            avg_response_time = sum(r['response_time_ms'] for r in successful_tests) / len(successful_tests)
            max_response_time = max(r['response_time_ms'] for r in successful_tests)
            min_response_time = min(r['response_time_ms'] for r in successful_tests)
            
            print(f"📊 Performance Summary:")
            print(f"   ✅ Successful tests: {len(successful_tests)}/{len(results)}")
            print(f"   ⚡ Average response time: {avg_response_time:.2f}ms")
            print(f"   🚀 Fastest response: {min_response_time:.2f}ms")
            print(f"   🐌 Slowest response: {max_response_time:.2f}ms")
        else:
            print("❌ No successful tests - check if the application is running")
    
    return results


async def test_concurrent_requests(base_url: str = "http://localhost:8000", concurrent_requests: int = 10):
    """Test concurrent request handling"""
    print(f"\n🔥 Testing {concurrent_requests} concurrent requests...")
    
    async def make_request(client: httpx.AsyncClient, request_id: int):
        start_time = time.time()
        try:
            response = await client.post(f"{base_url}/test")
            end_time = time.time()
            return {
                "request_id": request_id,
                "response_time_ms": (end_time - start_time) * 1000,
                "status_code": response.status_code,
                "success": response.status_code < 400
            }
        except Exception as e:
            end_time = time.time()
            return {
                "request_id": request_id,
                "response_time_ms": (end_time - start_time) * 1000,
                "error": str(e),
                "success": False
            }
    
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=concurrent_requests)
    ) as client:
        
        start_time = time.time()
        
        # Run concurrent requests
        tasks = [make_request(client, i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        successful_requests = [r for r in results if r['success']]
        
        if successful_requests:
            avg_response_time = sum(r['response_time_ms'] for r in successful_requests) / len(successful_requests)
            print(f"📈 Concurrent Test Results:")
            print(f"   ✅ Successful requests: {len(successful_requests)}/{concurrent_requests}")
            print(f"   ⏱️ Total test time: {total_time:.2f}ms")
            print(f"   ⚡ Average response time: {avg_response_time:.2f}ms")
            print(f"   🚀 Requests per second: {(concurrent_requests / (total_time / 1000)):.2f}")
        else:
            print("❌ All concurrent requests failed")


async def main():
    """Main test function"""
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🚀 FastAPI Performance Test Suite")
    print(f"🎯 Target: {base_url}")
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test basic endpoints
    await run_performance_tests(base_url)
    
    # Test concurrent handling
    await test_concurrent_requests(base_url, 10)
    
    print("\n🏁 Performance testing complete!")
    print("\n💡 Tips for Azure deployment:")
    print("   - Monitor response times < 500ms for good performance")
    print("   - Check Azure Application Insights for detailed metrics")
    print("   - Scale up if concurrent request handling is slow")


if __name__ == "__main__":
    asyncio.run(main())