#!/usr/bin/env python3
"""
Direct test - paste your API key below and run.
"""

# ============================================
# PASTE YOUR FULL API KEY HERE:
# ============================================
API_KEY = "PASTE_YOUR_KEY_HERE"
# ============================================

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, '.')

from google import genai
from google.genai import types


async def test():
    """Direct LLM test."""

    if API_KEY == "PASTE_YOUR_KEY_HERE":
        print("\n❌ Please edit test_direct.py and paste your API key at the top")
        print("   Look for: API_KEY = \"PASTE_YOUR_KEY_HERE\"")
        print("   Replace with your full key: AIzaSyAORX...pJwY\n")
        return False

    print("\n" + "="*70)
    print("Direct Gemini LLM Test")
    print("="*70)
    print(f"\nUsing API key: {API_KEY[:10]}...{API_KEY[-4:]}\n")

    # Load events
    events = []
    with open("imx500_events_remote.jsonl") as f:
        for i, line in enumerate(f):
            if i >= 48:
                break
            event = json.loads(line.strip())
            events.append(event)

    print(f"Loaded {len(events)} events\n")

    # Create client
    client = genai.Client(api_key=API_KEY)

    # Build prompt
    prompt = f"""Analyze these {len(events)} car detection events from an object detection camera.

Events: {len(events)} car detections over 60 minutes
Average confidence: 0.52

Please provide:
1. A brief summary (2-3 sentences)
2. Key insights
3. Any recommendations
"""

    # Try different model names
    models_to_try = [
        "gemini-1.5-flash",
        "models/gemini-1.5-flash",
        "gemini-1.5-pro",
        "models/gemini-1.5-pro",
        "gemini-pro",
        "models/gemini-pro",
    ]

    for model in models_to_try:
        print(f"🔄 Trying: {model}")
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )

            print(f"✅ SUCCESS with {model}!\n")
            print("="*70)
            print("LLM SUMMARY")
            print("="*70)
            print()
            print(response.text)
            print()
            print("="*70)
            print(f"✅ Model '{model}' works!")
            print("="*70)

            return True

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                print(f"   ❌ Not found")
            elif "429" in error_msg:
                print(f"   ❌ Quota exceeded")
            elif "403" in error_msg:
                print(f"   ❌ Permission denied")
            else:
                print(f"   ❌ {error_msg[:60]}")

    print("\n❌ All models failed. Here's what to do:")
    print("\n1. Check your API key is correct")
    print("2. Visit https://aistudio.google.com/app/prompts/new_chat")
    print("3. Try a test prompt there to verify your key works")
    print("4. Check quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas")

    return False


if __name__ == "__main__":
    success = asyncio.run(test())

    if success:
        print("\n🎉 SUCCESS! Your API key works!")
        print("\nNow you can run:")
        print(f"  export GEMINI_API_KEY='{API_KEY}'")
        print("  python src/agents/adk_enhanced/coordinator.py")

    sys.exit(0 if success else 1)
