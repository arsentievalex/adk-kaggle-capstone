# ADK Sales Copilot

**Multi-agent system that automates enterprise sales research from company analysis to personalized email drafts.**

---

## 🎯 What It Does

ResearchPilot transforms 2-4 hours of manual sales research into a 90-second automated workflow. Give it a company name and prospect, and it delivers:

- ✅ Recent company news, funding, and market position
- ✅ Competitive landscape analysis
- ✅ Technology stack and operational metrics
- ✅ Executive profile with recent talks and articles
- ✅ Strategic positioning mapped to Google Cloud solutions
- ✅ Personalized email draft and call script

**Result:** A complete, research-backed sales outreach package ready to send.

---

## 🏗️ Architecture

Built on **Google ADK** with a three-phase agent workflow:

```
Phase 1: Parallel Research (5 agents run concurrently)
    ├─ NewsResearcher → recent announcements
    ├─ CompetitorResearcher → market positioning  
    ├─ MetricsResearcher → revenue/headcount
    ├─ TechStackResearcher → technologies used
    └─ LeadResearcher → executive profiling

Phase 2: Strategy Development (1 agent)
    └─ PositioningStrategist → maps pain points to GC solutions

Phase 3: Outreach Generation (1 agent)
    └─ OutreachWriter → personalized email + call script
```

**Model:** Gemini 2.5 Flash  
**Tools:** Google Search, Exa MCP (LinkedIn/web search), load_web_page

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Google API Key (for Gemini)
- Exa API Key (optional, for enhanced executive profiling)

### Installation

```bash
# Clone the repository
git clone https://github.com/arsentievalex/adk-kaggle-capstone
cd adk-kaggle-capstone

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
EXA_API_KEY=your_exa_api_key_here  # Optional but recommended
```

### Run

```bash
python main.py
```

**Default target:** Researches Revolut and CIO Carlos Selonke

```python
user_query = "Research prospect '{PROSPECT_NAME}' and their company: '{PROSPECT_COMPANY}'."
```

---

## 📊 Sample Output

The system generates a markdown file (`sales_outreach.md`) containing:

**Email Draft:**
```
Subject: Edge computing meets AI: Vercel + Google Cloud

Hi Guillermo,

I caught your recent talk on the future of serverless at Next.js Conf...
[personalized opening based on research]

Companies like [relevant case study] are using Vertex AI to...
[solution mapping with proof points]

Would you be open to a 15-minute conversation about...
[low-friction CTA]
```

**Call Script:**
```
30-second voicemail opener with research hooks and clear value prop
```

---

## 🛠️ Tech Stack

- **Google ADK:** Agent orchestration framework
- **Gemini 2.5 Flash:** LLM for all agent reasoning
- **MCP (Model Context Protocol):** Integration with Exa for LinkedIn/web search
- **Python 3.13:** Async/await for concurrent research
- **Custom Observability:** Agent lifecycle tracking and performance metrics

---

## 📁 Project Structure

```
adk-kaggle-capstone/
├── main.py                 
├── requirements.txt        
├── sample_sales_outreach.md       
└── README.md              
```

---

## 🔧 Key Features

### Parallel Research
Five specialized agents run simultaneously to minimize latency while maintaining research depth.

### Hybrid Tool Strategy
- **Google Search:** Company news, competitors, metrics
- **Exa MCP:** Executive profiling via LinkedIn and web articles
- **Web Scraping:** Dynamic knowledge base retrieval (GC case studies)

### State Management
Each agent writes findings to specific state keys that downstream agents consume for sequential reasoning.

### Observability
Built-in logging tracks:
- Agent start/end times
- Tool invocations
- Duration metrics per phase

---

## 🚧 Limitations

- **Rate Limits:** Heavy API usage for complex prospects
- **No Caching:** Re-researches same company on every run
- **Single Session:** Doesn't persist data between runs
- **Manual Input:** Requires hardcoded company/CEO names

---

## 🔮 Roadmap

- [ ] Web UI for interactive research sessions
- [ ] CRM integration (Salesforce, HubSpot)
- [ ] Batch processing for multiple prospects
- [ ] Research caching and refresh logic
- [ ] A/B testing for outreach variants
- [ ] Real-time signal monitoring (funding, job posts)

---

## 📝 License

MIT License - feel free to use and modify for your sales workflows.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional research sources (Crunchbase, PitchBook)
- Industry-specific positioning templates
- Multi-language support for international sales
- Integration with more CRM platforms

---

## 💡 Use Cases

- **SDRs/BDRs:** Automate top-of-funnel research
- **Account Executives:** Prepare for discovery calls
- **Sales Engineers:** Technical landscape analysis
- **Marketing:** ABM campaign personalization
- **Founders:** Fast prospect validation

---

**Built with Google ADK | Powered by Gemini**
