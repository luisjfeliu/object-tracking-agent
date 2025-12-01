# Testing Gemini LLM Integration

## 🎯 Objective
Test the LLM-powered summarization to see AI-generated insights vs rule-based summaries.

## 📋 Prerequisites
- ✅ Enhanced ADK system (already installed)
- ✅ Event log with data (imx500_events_remote.jsonl)
- ⚠️ Gemini API key (you need to get this)

## 🚀 Quick Start (3 Steps)

### Step 1: Get Your Gemini API Key

1. Visit **https://aistudio.google.com/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"** or **"Get API Key"**
4. Copy the entire key (starts with `AIza...`)

**It's FREE** - No credit card required!

### Step 2: Test with Your API Key

Run one of these commands:

**Option A - Pass as argument:**
```bash
python test_llm_simple.py YOUR_API_KEY_HERE
```

**Option B - Set as environment variable:**
```bash
export GEMINI_API_KEY='YOUR_API_KEY_HERE'
python test_llm_simple.py
```

**Option C - Inline:**
```bash
GEMINI_API_KEY='YOUR_API_KEY_HERE' python test_llm_simple.py
```

### Step 3: Compare the Results

You'll see both:
- 📊 Rule-based summary (factual, structured)
- 🤖 LLM summary (natural language, insights)

## 📊 What You'll See

### Current Output (Rule-based - no API key)
```
Summary of 48 detections in the last 60 minutes:

Detections by category:
  - CAR: 48 (avg confidence: 0.52)

High activity categories:
  - car: 100.0% of detections

Unusual activity detected in 1 time window(s)
```

### Expected Output (LLM-powered - with API key)
```
Based on the analysis of 48 car detections over the past hour, the
camera system is performing consistently. The detections show moderate
confidence levels averaging 52%, which indicates reliable but potentially
improvable detection accuracy.

Key Observations:
• Cars dominate the detection stream at 100% of all events, which is
  expected for a traffic monitoring setup
• Detection confidence is moderate (52% average), suggesting the model
  is being appropriately cautious
• A spike in activity was detected in one time window, possibly
  indicating a traffic surge or busy period

Insights:
The system is functioning as designed for general traffic monitoring.
The confidence levels are reasonable for real-world conditions where
lighting, angles, and occlusion can vary.

Recommendations:
1. Monitor the high-activity time window to identify if it corresponds
   to predictable patterns (e.g., rush hour)
2. If false positives are a concern, consider raising the confidence
   threshold slightly
3. For school bus detection priority, ensure the model can effectively
   distinguish buses from standard cars - the current data shows only
   car detections, so bus detection capability should be validated
4. Consider logging additional metadata (time of day, weather) to
   correlate with detection quality
```

## 🎭 Try It Now!

I've created a simple test you can run. Here's what to do:

### 1. Get Your API Key
Open this link in your browser: **https://aistudio.google.com/apikey**

### 2. Run the Test
Once you have your key, run:
```bash
python test_llm_simple.py YOUR_KEY_HERE
```

Replace `YOUR_KEY_HERE` with your actual key.

### 3. Watch the Magic! ✨
You'll see the LLM generate natural language summaries with insights and recommendations.

## 🔍 Detailed Comparison

| Aspect | Rule-Based | LLM-Powered |
|--------|-----------|-------------|
| **Speed** | Instant (~2ms) | Fast (~500ms) |
| **Style** | Structured lists | Natural language |
| **Insights** | Basic stats | Patterns & anomalies |
| **Recommendations** | None | Actionable suggestions |
| **Cost** | Free | Free (with limits) |
| **Reliability** | 100% consistent | 99%+ consistent |

## 🛠️ Troubleshooting

### "Invalid API key"
- Make sure you copied the entire key
- Check for extra spaces at the beginning/end
- Try generating a new key

### "Quota exceeded"
- Free tier: 15 requests/minute, 1500/day
- Wait a minute and try again
- More than enough for this project

### Still showing "RULE-BASED"
Check if the key is set:
```bash
echo $GEMINI_API_KEY
```

If empty, set it:
```bash
export GEMINI_API_KEY='your-key'
```

### Network error
- Check internet connection
- Try again in a few seconds
- Verify you can access https://aistudio.google.com

## 📈 After Testing

Once you confirm LLM is working:

### 1. Run the Full Coordinator
```bash
export GEMINI_API_KEY='your-key'
python src/agents/adk_enhanced/coordinator.py
```

### 2. Set Permanently (Optional)
Add to `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Deploy on Raspberry Pi
Copy your enhanced system to the Pi:
```bash
# On your desktop
scp -r src/agents/adk_enhanced pi@raspberrypi:~/object-tracking-agent/src/agents/

# On the Pi
export GEMINI_API_KEY='your-key'
python src/agents/adk_enhanced/coordinator.py
```

## 🎓 For Kaggle Competition

The LLM summaries will make your submission stand out:

1. **Natural Language Analysis** - Not just numbers
2. **Pattern Detection** - Identifies anomalies automatically
3. **Actionable Insights** - Recommendations for improvement
4. **Professional Output** - Clean, readable reports

Include in your Kaggle notebook:
```python
# Setup API key from Kaggle Secrets
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
os.environ['GEMINI_API_KEY'] = secrets.get_secret("GEMINI_API_KEY")

# Run coordinator
coordinator = ObjectTrackingCoordinator(...)
await coordinator.run()
```

## 💡 Pro Tips

1. **Test First** - Always test with `test_llm_simple.py` before running the full coordinator
2. **Monitor Usage** - Check your quota at https://aistudio.google.com
3. **Keep Key Safe** - Don't commit to git, don't share publicly
4. **Fallback Works** - System automatically uses rule-based if LLM fails
5. **Custom Prompts** - Edit `summary_tools.py` to customize LLM prompts

## 📚 Additional Resources

- **Setup Guide**: `docs/GEMINI_SETUP.md`
- **Architecture**: `docs/adk_architecture.md`
- **Full README**: `docs/adk_enhanced_README.md`
- **Gemini Pricing**: https://ai.google.dev/pricing

## ✅ Success Checklist

- [ ] Got Gemini API key from aistudio.google.com
- [ ] Ran `test_llm_simple.py` with API key
- [ ] Saw "LLM Used: Yes" in output
- [ ] Compared rule-based vs LLM summaries
- [ ] Ran full coordinator with LLM
- [ ] (Optional) Set API key permanently

## 🎉 Ready to Test!

You now have everything you need. Just:
1. Get your API key (takes 30 seconds)
2. Run the test
3. Enjoy AI-powered summaries!

Questions? Check the troubleshooting section above or run:
```bash
python test_llm_simple.py --help
```
