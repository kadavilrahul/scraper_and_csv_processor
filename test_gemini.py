#!/usr/bin/env python3
"""
Test script to validate Gemini API key
"""

import requests
import json
import sys
import os

def load_env_file():
    """Load .env file manually"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")

def test_gemini_api(api_key=None, endpoint=None):
    """Test if the Gemini API key is valid"""
    
    # Load environment variables from .env
    load_env_file()
    
    # Use provided values or get from environment
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    if not endpoint:
        endpoint = os.getenv('GEMINI_API_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models/')
    
    # Ensure endpoint ends with /
    if not endpoint.endswith('/'):
        endpoint += '/'
    
    url = f"{endpoint}gemini-2.0-flash-exp:generateContent"
    print(f"Testing endpoint: {url}")
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    
    # Simple test prompt
    data = {
        "contents": [{
            "parts": [{
                "text": "Reply with just 'OK' if you receive this message."
            }]
        }]
    }
    
    try:
        print("Testing Gemini API key...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            print("✅ API key is valid and working!")
            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0].get('content', {})
                if 'parts' in content:
                    print(f"Response: {content['parts'][0].get('text', 'No text')[:100]}")
            return True
        elif response.status_code == 403:
            print("❌ API key is invalid or doesn't have permission")
            print(f"Error: {response.text[:200]}")
            return False
        elif response.status_code == 429:
            print("⚠️ Rate limit exceeded. API key is valid but quota exceeded.")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"Error: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Load from .env first
    load_env_file()
    
    print("Gemini API Key Tester")
    print("-" * 40)
    
    # Check if key exists in environment
    existing_key = os.getenv('GEMINI_API_KEY')
    existing_endpoint = os.getenv('GEMINI_API_ENDPOINT')
    
    if existing_key:
        print(f"Found API key in .env: {existing_key[:10]}...{existing_key[-4:]}")
        print(f"Found endpoint: {existing_endpoint or 'Using default'}")
        use_existing = input("\nUse existing configuration? (Y/n): ").strip().lower()
        
        if use_existing != 'n':
            if test_gemini_api():
                print("\n✅ API key test successful! Configuration is working.")
            else:
                print("\n❌ API key test failed. Please check your configuration.")
            sys.exit(0)
    
    # Prompt for new key
    api_key = input("\nEnter Gemini API key to test (or press Enter to use .env): ").strip()
    
    if not api_key and not existing_key:
        print("No API key provided or found in .env")
        sys.exit(1)
    
    # Test the API
    if test_gemini_api(api_key if api_key else None):
        print("\n✅ API key test successful! You can use this key in the eBay scraper.")
    else:
        print("\n❌ API key test failed. Please check your key and try again.")