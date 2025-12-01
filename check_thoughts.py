#!/usr/bin/env python3
"""Check if response has thoughts."""

import os
from google import genai
from google.genai import types

api_key = os.environ.get('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Summarize: 48 car detections in 60 minutes",
    config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=1000
    )
)

print("Finish reason:", response.candidates[0].finish_reason if response.candidates else "none")
print("Usage:", response.usage_metadata if hasattr(response, 'usage_metadata') else "none")

if response.candidates:
    candidate = response.candidates[0]
    print("\nCandidate content:", candidate.content)
    print("Content parts:", candidate.content.parts if candidate.content else "none")

    if candidate.content and candidate.content.parts:
        for i, part in enumerate(candidate.content.parts):
            print(f"\nPart {i}:")
            print(f"  Type: {type(part)}")
            print(f"  Has text: {hasattr(part, 'text')}")
            print(f"  Has thought: {hasattr(part, 'thought')}")
            if hasattr(part, 'text') and part.text:
                print(f"  Text: {part.text[:100]}")
            if hasattr(part, 'thought') and part.thought:
                print(f"  Thought: {part.thought[:100]}")

print("\nResponse.text:", response.text)
