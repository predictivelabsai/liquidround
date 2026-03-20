# LiquidRound - Multi-Agent M&A and IPO Deal Flow System

**Predictive Labs Ltd**

LiquidRound is an advanced multi-agent system designed to streamline M&A and IPO deal flow processes using LangGraph and Streamlit. The system provides intelligent workflow orchestration for buyer-led M&A, seller-led M&A, and IPO transactions.

## Features

- **Multi-Agent Architecture**: Specialized agents for different aspects of deal flow
- **Intelligent Workflow Routing**: Automatic classification of user queries into appropriate workflows
- **Interactive Chat Interface**: Streamlit-based UI with suggested queries
- **Comprehensive Logging**: Detailed logging and tracing of agent activities
- **Extensible Design**: Modular architecture for easy addition of new agents and workflows

## System Architecture

### Core Agents

1. **Orchestrator Agent**: Routes queries to appropriate workflows
2. **Target Finder Agent**: Identifies acquisition targets based on criteria
3. **Valuer Agent**: Performs financial analysis and valuation
4. **Synergy Analyst**: Analyzes potential synergies
5. **Bid Strategist**: Develops bidding strategies
6. **Seller Prep Agent**: Prepares companies for sale
7. **Market Outreach Agent**: Identifies potential buyers
8. **IPO Readiness Assessor**: Evaluates IPO readiness
9. **Memo Writer**: Creates investment committee memoranda

### Workflows

- **Buyer-Led M&A**: Target identification → Valuation → Synergy analysis → Bid strategy
- **Seller-Led M&A**: Seller preparation → Market outreach → Buyer identification
- **IPO**: Readiness assessment → Underwriter selection → Process planning

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kaljuvee/liquidround.git
cd liquidround
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your API keys
```

4. Run the application:
```bash
streamlit run Home.py
```

**Note**: The main application files are now organized in the `agents/` directory for better structure.

## Configuration

The system requires the following environment variables:

- `OPENAI_API_KEY`: OpenAI API key for LLM interactions
- `POLYGON_API_KEY`: (Optional) Polygon.io API key for financial data
- `EXA_API_KEY`: (Optional) Exa API key for enhanced search

## Usage

1. **Start the Application**: Run `streamlit run Home.py`
2. **Select Query Type**: Choose from suggested queries or enter your own
3. **Review Results**: The system will automatically route your query and execute the appropriate workflow
4. **Analyze Output**: Review agent results, financial analysis, and recommendations

### Example Queries

**Buyer-Led M&A:**
- "Find fintech acquisition targets with $10-50M revenue"
- "Looking to acquire a SaaS company in healthcare"

**Seller-Led M&A:**
- "Preparing to sell our B2B software company"
- "Need help finding buyers for our logistics business"

**IPO:**
- "Assessing IPO readiness for our tech company"
- "Planning to go public in the next 18 months"

## Testing

Run the test suite:
```bash
pytest
```

Test specific components:
```bash
pytest tests/test_agents.py
pytest tests/test_state.py
```

## Project Structure

```
liquidround/
├── Home.py                 # Main application entry point
├── agents/                # Core application and agent implementations
│   ├── Home.py            # Streamlit application
│   ├── workflow.py        # LangGraph workflow definition
│   ├── base_agent.py      # Base agent class
│   ├── orchestrator.py    # Workflow orchestrator
│   ├── target_finder.py   # Target identification agent
│   └── valuer.py          # Financial valuation agent
├── prompts/               # Agent system prompts (Markdown format)
│   ├── orchestrator.md
│   ├── target_finder.md
│   ├── valuer.md
│   └── ...
├── utils/                 # Utility modules
│   ├── state.py
│   ├── logging.py
│   └── config.py
├── tests/                 # Test suite
├── test-data/            # Test data files
├── logs/                 # Application logs
└── db/                   # Database files
```

## Development

### Adding New Agents

1. Create agent class in `agents/` directory
2. Add system prompt in `prompts/` directory
3. Update workflow in `workflow.py`
4. Add tests in `tests/` directory

### Customizing Prompts

Agent prompts are stored in the `prompts/` directory as `.md` (Markdown) files. Edit these files to customize agent behavior. The Markdown format allows for better formatting and documentation of prompts.

### Logging

The system provides comprehensive logging:
- Application logs in `logs/liquidround.log`
- Agent-specific logs in `logs/agent_*.log`
- Trace logs for detailed debugging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For questions or support, please open an issue on GitHub.

---

**Predictive Labs Ltd** - Advanced M&A and IPO Advisory Services