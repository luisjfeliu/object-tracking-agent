# Gemini LLM Setup Guide

## Quick Start

### 1. Get Your API Key

Visit **[Google AI Studio](https://aistudio.google.com/apikey)** and:

1. Sign in with your Google account
2. Click **"Create API Key"** or **"Get API Key"**
3. Copy the key (starts with `AIza...`)

### 2. Set the API Key

**Option A: For this session only**
```bash
export GEMINI_API_KEY='your-api-key-here'
```

**Option B: Permanently (recommended)**
```bash
# Add to your shell config (~/.bashrc or ~/.zshrc)
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**Option C: In the command**
```bash
GEMINI_API_KEY='your-key' python test_gemini_llm.py
```

### 3. Test the LLM

Run the interactive test:
```bash
python test_gemini_llm.py
```

Or test directly in code:
```bash
python -c "
import asyncio
from pathlib import Path
import json
import sys

sys.path.insert(0, '.')
from src.agents.adk_enhanced.agents.summary_agent import create_summary_agent

async def test():
    # Load events
    events = []
    with open('imx500_events_remote.jsonl') as f:
        for line in f:
            event = json.loads(line)
            if 'event_type' not in event:
                event['event_type'] = 'object_detected'
                event['details'] = event.copy()
            events.append(event)
            if len(events) >= 50:
                break

    # Test LLM
    agent = create_summary_agent()
    result = await agent.generate_summary_async(events, 60)

    print('='*70)
    print('LLM SUMMARY:')
    print('='*70)
    print(result['summary'])
    print()
    print(f\"Model: {result['metadata']['model']}\")
    print(f\"LLM Used: {result['metadata']['llm_used']}\")

asyncio.run(test())
"
```

## What You'll See

### Without API Key (Rule-based)
```
Summary of 48 detections in the last 60 minutes:

Detections by category:
  - CAR: 48 (avg confidence: 0.52)

High activity categories:
  - car: 100.0% of detections

Unusual activity detected in 1 time window(s)
```

### With API Key (LLM-powered)
```
Based on the 48 car detections over the past hour, the camera system
is functioning well with consistent detection performance. The average
confidence of 52% suggests the detections are reliable, though there's
room for optimization.

Key insights:
- Cars are the dominant object type (100% of detections)
- Detection confidence is moderate, averaging 52%
- A spike in activity was detected in one time window, suggesting
  possible traffic congestion or a busy period

Recommendations:
- Monitor the high-activity period to identify if it's a recurring
  pattern (e.g., rush hour)
- Consider adjusting the confidence threshold if false positives
  are an issue
- If school bus detection is the priority, ensure the model is
  properly distinguishing buses from regular cars
```

## Troubleshooting

### Error: "Invalid API key"
- Check that you copied the full key (starts with `AIza`)
- Make sure there are no extra spaces
- Generate a new key if needed

### Error: "API quota exceeded"
- Free tier: 60 requests per minute
- If exceeded, wait a minute and try again
- Consider upgrading for higher limits

### Error: "Network error"
- Check your internet connection
- Verify you can access aistudio.google.com
- Try again in a few seconds

### No error but using rule-based
Check if the key is actually set:
```bash
echo $GEMINI_API_KEY
```

If empty, set it again:
```bash
export GEMINI_API_KEY='your-key'
```

## API Key Security

**DO NOT:**
- ❌ Commit API keys to git
- ❌ Share keys publicly
- ❌ Include in screenshots

**DO:**
- ✅ Use environment variables
- ✅ Add to `.gitignore` if storing in files
- ✅ Rotate keys periodically
- ✅ Delete unused keys

Add to `.gitignore`:
```bash
echo '.env' >> .gitignore
echo '*.key' >> .gitignore
```

## Cost & Limits

**Gemini 2.0 Flash (Free Tier):**
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per day

**For this project:**
- Each summary: ~500-1000 tokens
- ~1000-2000 summaries per day
- Effectively unlimited for typical use

See [Gemini Pricing](https://ai.google.dev/pricing) for details.

## Next Steps

Once your API key is working:

1. **Run the test:**
   ```bash
   python test_gemini_llm.py
   ```

2. **Run the coordinator:**
   ```bash
   python src/agents/adk_enhanced/coordinator.py
   ```

3. **Watch the summaries:**
   - Every 200 events by default
   - Natural language analysis
   - Pattern detection
   - Actionable insights

Enjoy LLM-powered summaries! 🎉
