#!/usr/bin/env python3
"""List available Gemini models for your API key."""

import os
import sys
from google import genai

# Get API key from environment or argument
api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GEMINI_API_KEY')

if not api_key:
    print("❌ No API key provided")
    print("\nUsage:")
    print("  python list_models.py YOUR_API_KEY")
    print("  or")
    print("  GEMINI_API_KEY='your-key' python list_models.py")
    sys.exit(1)

print(f"Using API key: {api_key[:10]}...{api_key[-4:]}\n")

try:
    client = genai.Client(api_key=api_key)

    print("Available Gemini models:")
    print("="*70)

    models = client.models.list()
    gemini_models = []

    for model in models:
        if 'gemini' in model.name.lower():
            gemini_models.append(model.name)
            # Get supported methods
            methods = []
            if hasattr(model, 'supported_generation_methods'):
                methods = model.supported_generation_methods

            print(f"\n✓ {model.name}")
            if methods:
                print(f"  Methods: {', '.join(methods)}")

    if not gemini_models:
        print("❌ No Gemini models found!")
        print("\nAll models:")
        for model in models:
            print(f"  - {model.name}")
    else:
        print("\n" + "="*70)
        print(f"\nFound {len(gemini_models)} Gemini model(s)")
        print("\nTo use in your code:")
        print(f"  model_name = '{gemini_models[0]}'")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check your API key is valid")
    print("2. Visit: https://aistudio.google.com/apikey")
    print("3. Generate a new key if needed")
