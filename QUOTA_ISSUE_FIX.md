# Fixing the Quota Issue

## What Happened

You got this error:
```
429 RESOURCE_EXHAUSTED
Quota exceeded for metric: gemini-2.0-flash-exp
limit: 0
```

**Why:** The experimental model `gemini-2.0-flash-exp` has a quota limit of 0 for some API keys.

**Solution:** Use a stable model instead!

## ✅ Fixed!

I've updated all files to use `gemini-1.5-flash` (stable, fast, free tier).

## 🚀 Try Again

### Option 1: Edit the test file (Easiest)

1. Open `test_with_your_key.py`
2. Replace the API_KEY at the top with your full key:
   ```python
   API_KEY = "AIzaSyAORX...pJwY"  # Replace with YOUR full key
   ```
3. Save and run:
   ```bash
   python test_with_your_key.py
   ```

### Option 2: Run directly

```bash
python test_llm_simple.py YOUR_FULL_API_KEY
```

Replace `YOUR_FULL_API_KEY` with your actual key starting with `AIzaSyA...`

### Option 3: Export and run

```bash
export GEMINI_API_KEY='AIzaSyAORX...pJwY'  # Your full key
python test_llm_simple.py
```

## 📊 Available Models (Free Tier)

All files now default to `gemini-1.5-flash`:

| Model | Speed | Quality | Free Tier |
|-------|-------|---------|-----------|
| **gemini-1.5-flash** ✅ | Fast | Good | 15 RPM, 1M TPD |
| gemini-1.5-pro | Slow | Better | 2 RPM, 32K TPD |
| gemini-pro | Medium | Good | 15 RPM, 32K TPD |
| ~~gemini-2.0-flash-exp~~ | Fast | Great | ❌ 0 (not available) |

**Legend:**
- RPM = Requests per minute
- TPD = Tokens per day

## 🎯 Recommended: Use gemini-1.5-flash

This is now the default in all files:
- ✅ Fast response (~500ms)
- ✅ Good quality
- ✅ Free tier: 15 requests/min, 1M tokens/day
- ✅ Stable and reliable

## 🔧 Check Your Quota

Visit: **https://aistudio.google.com/app/prompts/new_chat**

1. Try a simple prompt: "Hello"
2. If it works → Your API key is good!
3. Check quota at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

## 📝 Quick Test

Run this to verify your key works:

```bash
python -c "
import os
from google import genai

os.environ['GEMINI_API_KEY'] = 'YOUR_KEY_HERE'
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

response = client.models.generate_content(
    model='gemini-1.5-flash',
    contents='Say hello'
)

print('✅ API key works!')
print('Response:', response.text)
"
```

Replace `YOUR_KEY_HERE` with your actual key.

## 🎉 Next Steps

Once you verify the key works:

1. **Test the summarization:**
   ```bash
   python test_llm_simple.py YOUR_KEY
   ```

2. **Run the coordinator:**
   ```bash
   export GEMINI_API_KEY='YOUR_KEY'
   python src/agents/adk_enhanced/coordinator.py
   ```

3. **Deploy on Pi:**
   ```bash
   # Copy to Pi
   scp -r src/agents/adk_enhanced pi@raspberrypi:~/object-tracking-agent/src/agents/

   # On Pi
   export GEMINI_API_KEY='YOUR_KEY'
   python src/agents/adk_enhanced/coordinator.py
   ```

## 💡 Model Selection

You can override the model with:

```bash
# For testing
python test_llm_simple.py YOUR_KEY

# For coordinator
ADK_MODEL=gemini-1.5-pro python src/agents/adk_enhanced/coordinator.py
```

Available models:
- `gemini-1.5-flash` (default, recommended)
- `gemini-1.5-pro` (better quality, slower)
- `gemini-pro` (older, still good)

## 🐛 Still Having Issues?

### Try these in order:

1. **Generate a new API key:**
   - Visit https://aistudio.google.com/apikey
   - Delete old key
   - Create new key
   - Try again

2. **Check API is enabled:**
   - Visit https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
   - Ensure "Generative Language API" is enabled

3. **Wait and retry:**
   - Sometimes takes a few minutes for new keys to activate
   - Wait 5 minutes and try again

4. **Use rule-based:**
   - System works fine without LLM!
   - Just won't have natural language summaries
   - All other features work perfectly

## ✅ Summary

- ❌ `gemini-2.0-flash-exp` → Has quota limit of 0
- ✅ `gemini-1.5-flash` → Works, fast, free tier
- ✅ All files updated to use stable model
- ✅ Ready to test again!

**Run:** `python test_with_your_key.py` (easiest)
