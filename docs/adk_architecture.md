# Enhanced ADK Multi-Agent Architecture

## Overview
Enhanced multi-agent coordination system using Google ADK for the IMX500 object tracking project.

## Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                   ADK Agent Coordinator                      │
│                 (Root Agent - Orchestrator)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌─────────────┐  ┌──────────────────┐
│   Ingestion  │  │     Bus     │  │   Summarization  │
│    Agent     │  │ Notification│  │   Agent (LLM)    │
│              │  │   Agent     │  │                  │
└──────┬───────┘  └──────┬──────┘  └────────┬─────────┘
       │                 │                   │
       │                 │                   │
       ▼                 ▼                   ▼
   [Tools]          [Tools]             [Tools]
   - tail_log       - send_alert       - analyze_events
   - parse_event    - format_msg       - generate_summary
   - filter_events  - log_alert        - detect_patterns
```

## Agent Definitions

### 1. Root Agent (Orchestrator)
**Type:** Sequential Agent
**Purpose:** Coordinate all sub-agents and manage event flow
**Responsibilities:**
- Receive events from ingestion agent
- Route events to appropriate handlers
- Trigger periodic summarization
- Maintain global state

### 2. Ingestion Agent
**Type:** Event Streaming Agent
**Purpose:** Tail JSONL log and parse events
**Tools:**
- `tail_events`: Async file tailing
- `parse_event`: JSON parsing and validation
- `filter_by_type`: Event type filtering

### 3. Bus Notification Agent
**Type:** Action Agent
**Purpose:** Handle bus detection alerts
**Tools:**
- `send_webhook`: POST to configured URL
- `format_alert_message`: Create alert payload
- `check_debounce`: Prevent duplicate alerts

### 4. Object Tracking Agent
**Type:** Stateful Agent
**Purpose:** Maintain consistent object track IDs
**Tools:**
- `update_tracks`: IoU-based tracking
- `get_track_history`: Query track data
- `prune_stale_tracks`: Remove old tracks

### 5. Summarization Agent (LLM-Powered)
**Type:** LLM Agent (Gemini)
**Purpose:** Generate intelligent summaries
**Tools:**
- `aggregate_events`: Group by category/time
- `detect_patterns`: Find anomalies
- `generate_report`: Natural language summary

## Implementation Components

### File Structure
```
src/agents/
├── adk_enhanced/
│   ├── __init__.py
│   ├── coordinator.py          # Root agent
│   ├── agents/
│   │   ├── ingestion_agent.py
│   │   ├── bus_agent.py
│   │   ├── tracking_agent.py
│   │   └── summary_agent.py
│   ├── tools/
│   │   ├── event_tools.py
│   │   ├── alert_tools.py
│   │   ├── tracking_tools.py
│   │   └── summary_tools.py
│   └── config/
│       ├── root_agent.yaml
│       └── agents_config.yaml
```

### Key Features

#### 1. Proper ADK Agent Integration
```python
from google.adk import Agent, Runner
from google.adk.tools import Tool

# Define agents using ADK Agent class
bus_agent = Agent(
    name="bus_notification_agent",
    description="Handles school bus detection alerts",
    tools=[send_webhook_tool, format_alert_tool]
)
```

#### 2. LLM-Powered Summarization
```python
from google.genai import types
from google.adk.models import get_model

summary_agent = Agent(
    name="summary_agent",
    model=get_model("gemini-2.0-flash-exp"),
    instructions="""Analyze object detection events and provide:
    1. Summary of detected objects
    2. Notable patterns or anomalies
    3. Recommendations for action""",
    tools=[aggregate_events_tool, detect_patterns_tool]
)
```

#### 3. Proper Task Routing
```python
from google.adk.flows import sequential_flow, parallel_flow

# Sequential: Ingest -> Process -> Summarize
main_flow = sequential_flow([
    ingestion_agent,
    parallel_flow([bus_agent, tracking_agent]),
    summary_agent
])
```

#### 4. State Management
```python
from google.adk.memory import InMemoryStore

# Track agent state across events
state_store = InMemoryStore()
tracking_agent.memory = state_store
```

#### 5. Event-Driven Architecture
```python
from google.adk.events import EventBus

event_bus = EventBus()

# Subscribe agents to specific events
event_bus.subscribe("bus_detected", bus_agent)
event_bus.subscribe("object_detected", tracking_agent)
event_bus.subscribe("summarize_request", summary_agent)
```

## Configuration

### Environment Variables
```bash
# ADK Configuration
ADK_PROJECT_ID=your-project-id
ADK_LOCATION=us-central1
ADK_MODEL=gemini-2.0-flash-exp

# Application Settings
IMX500_LOG_PATH=~/imx500_events.jsonl
ADK_BUS_WEBHOOK_URL=https://your-webhook
ADK_SUMMARY_WINDOW_MIN=30
ADK_USE_TRACKER=1

# LLM Settings
GEMINI_API_KEY=your-api-key
```

### Agent Configuration (YAML)
```yaml
# config/root_agent.yaml
name: object_tracking_coordinator
type: sequential_agent
description: Coordinates object tracking multi-agent system

sub_agents:
  - ingestion_agent
  - bus_notification_agent
  - tracking_agent
  - summary_agent

coordination_strategy: event_driven
concurrency: parallel_bus_tracking
```

## Benefits of Enhanced Architecture

1. **Proper Agent Abstraction**
   - Each agent is a first-class ADK Agent
   - Clear separation of concerns
   - Easy to test and maintain

2. **LLM Integration**
   - Natural language summaries
   - Pattern detection
   - Anomaly identification

3. **Scalability**
   - Parallel agent execution
   - Event-driven coordination
   - State management for long-running processes

4. **Observability**
   - ADK telemetry integration
   - Structured logging
   - Performance metrics

5. **Extensibility**
   - Easy to add new agents
   - Tool-based architecture
   - Configuration-driven

## Migration Path

1. **Phase 1:** Create new agent definitions using ADK Agent class
2. **Phase 2:** Implement tools for each agent
3. **Phase 3:** Add LLM-powered summarization
4. **Phase 4:** Integrate event-driven coordination
5. **Phase 5:** Add state management and memory
6. **Phase 6:** Testing and validation

## Testing Strategy

1. **Unit Tests:** Test each agent independently
2. **Integration Tests:** Test agent coordination
3. **End-to-End Tests:** Test with real event log
4. **Performance Tests:** Measure latency and throughput
