#!/usr/bin/env python3

import requests
import json
import subprocess
import sys
import time
import uuid

def get_gateway_url():
    """Auto-detect the Gateway URL using kubectl"""
    try:
        result = subprocess.run([
            'kubectl', 'get', 'gateway', 'ai-gateway', 
            '-o', 'jsonpath={.status.addresses[0].value}'
        ], capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            return f"http://{result.stdout.strip()}"
        else:
            print("Gateway address not found. Make sure the Gateway is deployed and has an address.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error getting gateway URL: {e}")
        return None

def test_model_with_rate_limit(gateway_url, model_name, user_id, test_name):
    """Test a specific model through the AI Gateway with rate limiting"""
    print(f"\n=== Testing {test_name} (User: {user_id}) ===")
    
    headers = {
        'Content-Type': 'application/json',
        'x-ai-eg-model': model_name,
        'x-user-id': user_id  # Required for rate limiting
    }
    
    endpoint = "/v1/completions"
    payload = {
        "prompt": f"Hello from {model_name}! Please respond briefly.",
        "max_tokens": 50,  # Smaller to test token limits
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            f"{gateway_url}{endpoint}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"User ID: {user_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {test_name}")
            content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
            print(f"Response: {content[:100]}...")
        elif response.status_code == 429:
            print(f"🚫 RATE LIMITED: {test_name}")
            print(f"Rate limit exceeded for user {user_id}")
            print(f"Response: {response.text}")
        else:
            print(f"❌ FAILED: {test_name}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {test_name} - {e}")

def test_rate_limiting_scenarios(gateway_url):
    """Test various rate limiting scenarios"""
    print("\n🔒 Testing Rate Limiting Scenarios")
    print("=" * 50)
    
    # Test 1: Normal usage within limits
    print("\n📊 Test 1: Normal usage within limits")
    user1 = "user-normal-001"
    test_model_with_rate_limit(gateway_url, "openai/gpt-oss-20b", user1, "Normal Usage")
    
    # Test 2: Rapid requests to trigger request-based rate limit
    print("\n📊 Test 2: Rapid requests (should trigger rate limit)")
    user2 = "user-rapid-002"
    for i in range(5):
        print(f"\nRequest {i+1}/5:")
        test_model_with_rate_limit(gateway_url, "openai/gpt-oss-20b", user2, f"Rapid Request {i+1}")
        time.sleep(0.5)  # Small delay between requests
    
    # Test 3: Different users should have separate limits
    print("\n📊 Test 3: Different users (separate limits)")
    user3 = "user-separate-003"
    test_model_with_rate_limit(gateway_url, "openai/gpt-oss-20b", user3, "Separate User Limits")
    
    # Test 4: Model-specific limits
    print("\n📊 Test 4: Model-specific limits")
    user4 = "user-model-004"
    test_model_with_rate_limit(gateway_url, "openai/gpt-oss-20b", user4, "Expensive Model")
    test_model_with_rate_limit(gateway_url, "NousResearch/Llama-3.2-1B", user4, "Regular Model")

def main():
    print("🚀 AI Gateway Multi-Model Rate Limiting Test")
    print("=" * 60)
    
    # Auto-detect Gateway URL
    gateway_url = get_gateway_url()
    if not gateway_url:
        print("❌ Could not determine Gateway URL. Exiting.")
        sys.exit(1)
    
    print(f"Gateway URL: {gateway_url}")
    
    # Test basic functionality first
    print("\n🧪 Basic Functionality Test")
    models_to_test = [
        ("openai/gpt-oss-20b", "gpt-oss-20b-vllm"),
        ("NousResearch/Llama-3.2-1B", "Llama-3.2-1B")
    ]
    
    base_user = "user-basic-test"
    for model_name, test_name in models_to_test:
        test_model_with_rate_limit(gateway_url, model_name, base_user, test_name)
    
    # Test rate limiting scenarios
    test_rate_limiting_scenarios(gateway_url)
    
    print(f"\n🎯 Rate Limiting Test Complete!")
    print("=" * 60)
    print("📋 Rate Limits Configured:")
    print("• Input tokens: 50K per hour per user")
    print("• Output tokens: 25K per hour per user") 
    print("• Total tokens: 75K per hour per user")
    print("• Requests: 60 per minute per user")
    print("• Expensive model (gpt-oss-20b): 30 per minute per user")
    print("\n💡 Tips:")
    print("• Use 'x-user-id' header to identify users")
    print("• Rate limits are enforced per user ID")
    print("• 429 status code indicates rate limit exceeded")

if __name__ == "__main__":
    main()
