#!/usr/bin/env python3
"""Debug the Gemini response structure."""

import os
from google import genai
from google.genai import types

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("Set GEMINI_API_KEY first")
    exit(1)

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Say hello in 10 words",
    config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=1000
    )
)

print("Response type:", type(response))
print("\nResponse attributes:", dir(response))
print("\nResponse.text exists?", hasattr(response, 'text'))
if hasattr(response, 'text'):
    print("Response.text:", response.text)

print("\nResponse.candidates exists?", hasattr(response, 'candidates'))
if hasattr(response, 'candidates'):
    print("Number of candidates:", len(response.candidates))
    if response.candidates:
        candidate = response.candidates[0]
        print("\nCandidate type:", type(candidate))
        print("Candidate attributes:", [x for x in dir(candidate) if not x.startswith('_')])

        if hasattr(candidate, 'content'):
            content = candidate.content
            print("\nContent type:", type(content))
            print("Content attributes:", [x for x in dir(content) if not x.startswith('_')])

            if hasattr(content, 'parts'):
                print("\nParts:", content.parts)
                if content.parts:
                    part = content.parts[0]
                    print("Part type:", type(part))
                    print("Part attributes:", [x for x in dir(part) if not x.startswith('_')])
                    print("\nPart.text:", part.text if hasattr(part, 'text') else "NO TEXT ATTRIBUTE")
