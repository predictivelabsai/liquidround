"""
Command DSL parser for LiquidRound.
Colon syntax: news:TSLA, profile:MSFT, score:buyer=PE,target=Acme, etc.
"""
from typing import Optional, Tuple, Dict, List


# All recognized command prefixes
COMMANDS = {
    # Research
    "news", "profile", "financials", "analysts", "valuation", "movers",
    # M&A specific
    "targets", "buyers", "ipo", "score", "research",
    # Tools
    "upload", "deals", "market", "tools", "settings", "docs",
    # Utility
    "help", "clear",
}


def parse_command(user_input: str) -> Tuple[Optional[str], str, Dict[str, str]]:
    """
    Parse colon-syntax commands.

    Returns: (command, subject, params)
      - command: the command name or None if free-form chat
      - subject: the primary argument (ticker, company name, etc.)
      - params: dict of key:value params

    Examples:
      "news:TSLA"              -> ("news", "TSLA", {})
      "news:TSLA limit:5"      -> ("news", "TSLA", {"limit": "5"})
      "profile:MSFT"           -> ("profile", "MSFT", {})
      "score:buyer=PE,target=Acme" -> ("score", "", {"buyer": "PE", "target": "Acme"})
      "targets industry:fintech revenue:20-100M" -> ("targets", "", {"industry": "fintech", "revenue": "20-100M"})
      "Find me fintech targets" -> (None, "", {})  -- free-form chat
      "help"                   -> ("help", "", {})
      "clear"                  -> ("clear", "", {})
    """
    text = user_input.strip()
    if not text:
        return (None, "", {})

    parts = text.split()
    first = parts[0]

    # Simple commands (no colon)
    if first.lower() in ("help", "h", "?"):
        return ("help", "", {})
    if first.lower() in ("clear", "cls"):
        return ("clear", "", {})
    if first.lower() == "movers":
        direction = parts[1] if len(parts) > 1 else "both"
        return ("movers", direction, {})

    # Colon syntax: command:subject
    if ":" in first:
        cmd, subject = first.split(":", 1)
        cmd = cmd.lower()
        if cmd not in COMMANDS:
            return (None, "", {})  # Not a known command, treat as chat

        # Parse remaining key:value or key=value params
        params = {}
        for part in parts[1:]:
            if ":" in part:
                k, v = part.split(":", 1)
                params[k.lower()] = v
            elif "=" in part:
                k, v = part.split("=", 1)
                params[k.lower()] = v
            else:
                # Bare word — append to subject
                subject = f"{subject} {part}" if subject else part

        # Handle score:buyer=X,target=Y as comma-separated params in subject
        if cmd == "score" and "," in subject:
            for kv in subject.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    params[k.strip().lower()] = v.strip()
            subject = ""

        return (cmd, subject.strip(), params)

    # Word-prefix commands without colon: "targets fintech" etc.
    if first.lower() in COMMANDS:
        cmd = first.lower()
        params = {}
        subject_parts = []
        for part in parts[1:]:
            if ":" in part:
                k, v = part.split(":", 1)
                params[k.lower()] = v
            else:
                subject_parts.append(part)
        return (cmd, " ".join(subject_parts), params)

    # Free-form chat
    return (None, "", {})


def get_help_text() -> str:
    return """**LiquidRound Commands**

**Research**
- `news:TSLA` — company news and recent developments
- `profile:MSFT` — company profile, sector, market cap
- `financials:AAPL` — revenue, EBITDA, margins, growth
- `analysts:GOOGL` — analyst ratings and price targets
- `valuation:AAPL,MSFT` — compare valuation metrics
- `movers` — top market movers (gainers & losers)

**M&A Workflows**
- `targets industry:fintech revenue:20-100M` — find acquisition targets
- `buyers company:LogisticsCo revenue:15M` — find strategic buyers
- `ipo company:TechCo industry:SaaS` — IPO readiness assessment
- `score buyer:Salesforce target:HubSpot` — synergy scoring (7 dimensions)
- `score doc:filename.pdf` — analyze document and find best buyer matches
- `research:cybersecurity M&A` — deep research via EXA + Tavily

**Documents**
- `docs` — list all uploaded documents with view/score actions
- Upload via paperclip button — auto-opens PDF viewer in right pane
- `score doc:filename.pdf` — parse document, extract company profile, score buyer matches

**Tools**
- `deals` — deal history
- `market` — sector performance heatmap
- `tools` — M&A platform tools (Deal Room, CIM, LOI, DD, etc.)
- `settings` — view LLM and API configuration

**General**
- `help` — show this reference
- `clear` — clear chat history
- Or just type a question in plain English!
"""
