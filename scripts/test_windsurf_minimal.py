#!/usr/bin/env python3
"""
Minimal test for Windsurf provider with free models.

This script tests the Windsurf provider with a single free model
using only essential dependencies.

Usage:
    python3 scripts/test_windsurf_minimal.py

Environment variables:
    WINDSURF_API_KEY: Your Windsurf API key (required)
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from providers.windsurf import WindsurfLLM
except ImportError as e:
    print(f"Error importing WindsurfLLM: {e}")
    print("Please install required dependencies:")
    print("  pip install requests tenacity")
    sys.exit(1)

# Test with a single free model
TEST_MODEL = "deepseek-v3"  # Using a single free model to minimize dependencies

def main():
    print("Windsurf Minimal Test")
    print("=" * 50)
    
    # Check API key
    api_key = os.environ.get("WINDSURF_API_KEY")
    if not api_key:
        print("ERROR: WINDSURF_API_KEY environment variable is required")
        print("Run: python -m providers.get_windsurf_token")
        sys.exit(1)
    
    print(f"Testing model: {TEST_MODEL}")
    print("-" * 50)
    
    try:
        # Initialize the model with direct mode to avoid LS detection
        print("Initializing WindsurfLLM...")
        llm = WindsurfLLM(model_name=TEST_MODEL)
        
        # Simple test prompt
        prompt = "What is the capital of France? Answer in one word."
        print(f"\nSending prompt: {prompt}")
        
        # Make the API call
        start_time = time.time()
        response = llm.invoke([{"role": "user", "content": prompt}])
        elapsed = time.time() - start_time
        
        # Process the response
        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
            
        print(f"\nResponse ({elapsed:.2f}s):")
        print("-" * 40)
        print(content.strip())
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure you have the required dependencies installed:")
        print("  pip install requests tenacity")
        sys.exit(1)

if __name__ == "__main__":
    main()
