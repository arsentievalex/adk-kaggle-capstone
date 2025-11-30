import asyncio
import os
import sys
import time
import logging
import json
import dotenv
import urllib.parse
from typing import Dict, Any, Optional, Tuple

# Import ADK core components
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search, BaseTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# Import MCP components
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams
from google.adk.tools import FunctionTool

# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"
APP_NAME = "sales_research_app"
USER_ID = "sales_rep_01"
SESSION_ID = "session_001"

# Load environment variables from .env file
dotenv.load_dotenv()

# Sample Sales Rep Details
SALES_REP_NAME = "John Doe"
SALES_REP_TITLE = "Senior Account Executive"

# Sample Prospect Details
PROSPECT_COMPANY = "Revolut"
PROSPECT_NAME = "Carlos Selonke"

# Knowledge Base URL
GC_USE_CASES_URL = "https://cloud.google.com/transform/101-real-world-generative-ai-use-cases-from-industry-leaders"

# --- 0. Observability & Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [OBSERVABILITY] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ADK_Observer")

def on_agent_start(callback_context: CallbackContext) -> None:
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    start_time_key = f"metrics:start_time:{invocation_id}:{agent_name}"
    callback_context.state[start_time_key] = time.time()
    logger.info(f"▶️  STARTED Agent: {agent_name}")
    return None

def on_agent_end(callback_context: CallbackContext) -> None:
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id
    
    # 1. Metrics Calculation
    start_time_key = f"metrics:start_time:{invocation_id}:{agent_name}"
    start_time = callback_context.state.get(start_time_key)
    duration_msg = ""
    if start_time:
        duration = time.time() - start_time
        duration_msg = f"({duration:.2f}s)"
    
    logger.info(f"⏹️  FINISHED Agent: {agent_name} {duration_msg}")

    # 2. Intermediate Output Logging
    # Map agent names to the keys where they store their results
    output_map = {
        "NewsResearcher": "news_data",
        "CompetitorResearcher": "competitor_data",
        "MetricsResearcher": "metrics_data",
        "TechStackResearcher": "techstack_data",
        "LeadResearcher": "lead_data",
        "PositioningStrategist": "positioning_strategy"
    }

    # If this agent has an output we care about, print it
    if agent_name in output_map:
        state_key = output_map[agent_name]
        # Retrieve the data from the session state
        data = callback_context.state.get(state_key)
        
        if data:
            print(f"\n{'-'*20} INTERMEDIATE OUTPUT: {agent_name} {'-'*20}")
            print(str(data).strip())
            print(f"{'-'*65}\n")

    return None

def on_tool_start(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> None:
    logger.info(f"   🛠️  TOOL CALL: {tool.name} by {tool_context.agent_name}")
    return None

# --- 1. Agent Instructions ---
NEWS_INSTRUCTION = """
You are a News Analyst. Find recent, relevant news about the target company.
1. Use `Google Search` to find news from the last 6-12 months 
(launches, funding, expansion, disputes, legal issues, layoffs, M&A, leadership changes, etc.).
2. Output a bulleted list of the top 3 most relevant news items.
"""
COMPETITOR_INSTRUCTION = """
You are a Market Analyst. Identify the target company's competitive landscape.
1. Use `Google Search` to identify top 3 direct competitors.
2. Identify how the target differentiates itself.
3. Output a summary of their competitive position.
"""
METRICS_INSTRUCTION = """
You are a Financial Analyst. Find key operating metrics.
1. Use `Google Search` to find: Estimated Revenue, Headcount, Number of Customers, and YoY Growth.
2. Output a concise summary of their size and stage.
"""
TECHSTACK_INSTRUCTION = """
You are a Technology Investigator. Infer the target company's tech stack. Focus ONLY on paid/vendor tech. DO NOT list open source or common frameworks.
1. Use `Google Search` to look for job postings or engineering blogs.
2. Identify key vendor technologies (CRM, Marketing/HR/Financial platforms).
3. Output a list of identified technologies.
"""
LEAD_INSTRUCTION = """
You are an Executive Profiler. Research the specific prospect.
1. Use `linkedin_search` for profile, title, work history and skills.
2. Use `web_search_exa` for interviews, articles, or talks.
3. Output a professional bio summary.
"""
POSITIONING_INSTRUCTION = f"""
You are a Google Cloud Solutions Architect and Strategist.
Your goal is to map the prospect's needs to Google Cloud's AI portfolio.
**Inputs Available in State:**
- Company Research: {{news_data}}, {{competitor_data}}, {{metrics_data}}, {{techstack_data}}
- Lead Profile: {{lead_data}}
**Your Tasks:**
1. **Analyze Research**: Identify 2-3 key pain points or opportunities based on their size, stack, and recent news.
2. **Fetch Knowledge**: Use the `load_web_page` tool to read the "101 Real World Gen AI Use Cases" page:
   URL: {GC_USE_CASES_URL}
3. **Select Case Studies**: From the page content, find the 3 most relevant case studies that match this prospect's industry or pain points.
4. **Formulate Strategy**:
   - How does Google Cloud (Vertex AI, Gemini, NotebookLM, etc.) solve their specific problems?
   - Connect the selected case studies as proof points.
**Output Format (Save to `positioning_strategy`):**
## Strategic Analysis
[Analysis of pain points]
## Recommended Solution Angle
[Mapping to specific GC products]
## Relevant Proof Points
1. [Company Name]: [Why it's relevant to this prospect]
2. ...
3. ...
"""
OUTREACH_INSTRUCTION = f"""
You are a Senior Sales Copywriter.
Your goal is to write the actual messages to the prospect using the strategy provided by the Positioning Strategist.
**Inputs:**
- Lead Profile: {{lead_data}}
- Positioning Strategy: {{positioning_strategy}}
- Sales Rep Name: {SALES_REP_NAME} ({SALES_REP_TITLE})
**Your Task:**
1. **Email Draft**: Write a high-impact cold email to the lead.
   - Subject Line: Punchy and relevant.
   - Opening: Reference specific research (e.g., "Saw your talk on...", "Congrats on the funding...").
   - Value Prop: Use the `positioning_strategy` to pitch the solution and cite ONE relevant case study.
   - Call to Action: Low friction.
   - Sign off: Use the Sales Rep Name.
   
2. **Call Script**: A 30-second talk track for a voicemail or cold call opening.
**Style:** Concise, professional, not "salesy".

Return ONLY the email and call script text, nothing else.
"""

# --- 2. Helper Functions ---
def create_exa_toolset() -> Optional[MCPToolset]:
    """Initializes the Exa MCP toolset if the API key is present."""
    exa_api_key = os.environ.get("EXA_API_KEY", "")
    if not exa_api_key:
        logger.warning("EXA_API_KEY not set. LeadProfiler will default to Google Search.")
        return None
    # 1. Encode enabled tools
    enabled_tools = ["linkedin_search", "web_search_exa"]
    encoded_tools = urllib.parse.quote(json.dumps(enabled_tools))
    
    # 2. Construct URL
    exa_url = f"https://mcp.exa.ai/mcp?exaApiKey={exa_api_key}&enabledTools={encoded_tools}"
    
    # 3. Create toolset with StreamableHTTPServerParams
    return MCPToolset(
        connection_params=StreamableHTTPServerParams(url=exa_url)
    )

def build_agents(exa_toolset: Optional[MCPToolset]) -> SequentialAgent:
    """Constructs the agent team hierarchy."""
    
    # Web Loader Tool
    web_loader_tool = FunctionTool(load_web_page)
    # Common Config
    search_agent_config = {
        "model": MODEL_NAME,
        "tools": [google_search],
        "disallow_transfer_to_parent": True,
        "disallow_transfer_to_peers": True,
        "before_agent_callback": on_agent_start,
        "after_agent_callback": on_agent_end,
        "before_tool_callback": on_tool_start
    }

    # Research Specialists
    news_agent = LlmAgent(name="NewsResearcher", instruction=NEWS_INSTRUCTION, output_key="news_data", **search_agent_config)
    competitor_agent = LlmAgent(name="CompetitorResearcher", instruction=COMPETITOR_INSTRUCTION, output_key="competitor_data", **search_agent_config)
    metrics_agent = LlmAgent(name="MetricsResearcher", instruction=METRICS_INSTRUCTION, output_key="metrics_data", **search_agent_config)
    techstack_agent = LlmAgent(name="TechStackResearcher", instruction=TECHSTACK_INSTRUCTION, output_key="techstack_data", **search_agent_config)
    
    # Lead Researcher (Uses Exa if available)
    lead_agent = LlmAgent(
        name="LeadResearcher",
        model=MODEL_NAME,
        instruction=LEAD_INSTRUCTION,
        output_key="lead_data",
        tools=[exa_toolset] if exa_toolset else [google_search],
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
        before_agent_callback=on_agent_start,
        after_agent_callback=on_agent_end,
        before_tool_callback=on_tool_start
    )

    # Parallel Team
    parallel_research_team = ParallelAgent(
        name="ParallelResearchTeam",
        sub_agents=[news_agent, competitor_agent, metrics_agent, techstack_agent, lead_agent],
        before_agent_callback=on_agent_start,
        after_agent_callback=on_agent_end
    )

    # Positioning Strategist
    positioning_agent = LlmAgent(
        name="PositioningStrategist",
        model=MODEL_NAME,
        instruction=POSITIONING_INSTRUCTION,
        output_key="positioning_strategy",
        tools=[web_loader_tool],
        before_agent_callback=on_agent_start,
        after_agent_callback=on_agent_end,
        before_tool_callback=on_tool_start
    )

    # Outreach Writer
    outreach_agent = LlmAgent(
        name="OutreachWriter",
        model=MODEL_NAME,
        instruction=OUTREACH_INSTRUCTION,
        before_agent_callback=on_agent_start,
        after_agent_callback=on_agent_end
    )

    # Root Orchestrator
    return SequentialAgent(
        name="LeadResearchSystem",
        sub_agents=[
            parallel_research_team,
            positioning_agent,     
            outreach_agent         
        ],
        before_agent_callback=on_agent_start,
        after_agent_callback=on_agent_end
    )

# --- 3. Runtime Setup ---
async def main():
    # Credentials check
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
        print("Error: GOOGLE_API_KEY not found.")
        return
    
    # Initialize Resources INSIDE the async loop to prevent context errors
    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    
    # Create Tools & Agents
    exa_toolset = create_exa_toolset()
    root_agent = build_agents(exa_toolset)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    print(f"🚀 Starting Sales System (Rep: {SALES_REP_NAME})...")
    print("----------------------------------------------------------------")

    user_query = f"Research prospect '{PROSPECT_NAME}' and their company: '{PROSPECT_COMPANY}'."
    print(f"TARGET: {user_query}\n")
    
    content = types.Content(role='user', parts=[types.Part(text=user_query)])
    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
            if event.is_final_response() and event.content:
                if event.author == "OutreachWriter":
                    final_text = event.content.parts[0].text

                    print(f"\n================================================================")
                    print(f"📧 FINAL OUTREACH DRAFT")
                    print(f"================================================================\n")
                    print(final_text)
                    
                    # Save to file
                    filename = "sales_outreach.md"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(final_text)
                    print(f"\n✅ Saved outreach draft to: {os.path.abspath(filename)}")
                
                elif event.author == "PositioningStrategist":
                    print(f"\n[DEBUG] Positioning Strategy Generated...\n")
    finally:
        # Cleanup MCP toolset if it was created
        if exa_toolset:
            print("\nClosing Exa toolset connection...")
            try:
                await exa_toolset.close()
            except Exception as e:
                logger.warning(f"Error during toolset cleanup: {e}")
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
