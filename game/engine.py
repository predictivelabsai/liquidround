"""Deal Street game engine — state management and game logic.

IB-flavored RPG: pitch mandates, structure deals, run diligence, close, collect fees.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

DB_SCHEMA = os.getenv("COMPANY_DB_SCHEMA", "pehero")

CHARACTERS = {
    "rainmaker": {
        "name": "Alex Voss",
        "title": "The Rainmaker",
        "role": "MD, Head of M&A",
        "icon": "\U0001f451",
        "ability": "Voss Special — mount an aggressive valuation defense once per round that shifts price 15% in your favour.",
        "start_capital": 0,
        "start_knowledge": 3,
        "start_network": 5,
        "start_reputation": 3,
        "description": (
            "A legendary MD who opens doors no one else can. CEOs take his calls, "
            "boards clear their calendars, and rival banks lose mandates when he walks in."
        ),
    },
    "modeler": {
        "name": "Priya Sharma",
        "title": "The Modeler",
        "role": "VP, Tech & Consumer M&A",
        "icon": "\U0001f4ca",
        "ability": "Deep Model — build a forensic financial model once per round that reveals hidden value or risk.",
        "start_capital": 0,
        "start_knowledge": 5,
        "start_network": 2,
        "start_reputation": 3,
        "description": (
            "An Excel wizard whose models are legendary on the Street. She sees the story "
            "behind the numbers — but sometimes the spreadsheet misses what a handshake reveals."
        ),
    },
    "bull": {
        "name": "Marcus Reynolds",
        "title": "The Bull",
        "role": "Director, Leveraged Finance",
        "icon": "\U0001f4b0",
        "ability": "LevFin Push — structure an aggressive LBO once per round that maximises leverage for the buyer.",
        "start_capital": 0,
        "start_knowledge": 3,
        "start_network": 4,
        "start_reputation": 2,
        "description": (
            "A leveraged finance specialist with deep capital markets connections. "
            "He can structure anything — but his aggressive instincts sometimes push deals too far."
        ),
    },
    "strategist": {
        "name": "Sophie Laurent",
        "title": "The Strategist",
        "role": "Associate, ECM",
        "icon": "\U0001f3af",
        "ability": "Market Timing — predict the next market window once per round to optimise IPO/deal timing.",
        "start_capital": 0,
        "start_knowledge": 4,
        "start_network": 2,
        "start_reputation": 3,
        "description": (
            "An ECM specialist with an uncanny sense of market timing. She's called the top "
            "and bottom of three IPO windows — but even she can't predict black swans."
        ),
    },
    "grinder": {
        "name": "Derek Chen",
        "title": "The Grinder",
        "role": "Analyst",
        "icon": "\U0001f4aa",
        "ability": "All-Nighter — take an extra analysis action once per round that others would need a full stage to complete.",
        "start_capital": 0,
        "start_knowledge": 4,
        "start_network": 1,
        "start_reputation": 2,
        "description": (
            "The hardest-working analyst on the floor. First in, last out, and his pitch books "
            "are flawless. He'll outwork anyone — but even grinders burn out eventually."
        ),
    },
    "insider": {
        "name": "Dr. Elena Petrova",
        "title": "The Insider",
        "role": "Ex-banker, Corp Dev VP at Horizon Dynamics",
        "icon": "\U0001f50d",
        "ability": "Inside Track — get proprietary intelligence on a target once per round from your corporate network.",
        "start_capital": 0,
        "start_knowledge": 4,
        "start_network": 3,
        "start_reputation": 3,
        "description": (
            "An ex-banker who crossed to the corporate side. She knows how both sides think, "
            "and her corporate network gives her intelligence no banker can match."
        ),
    },
}

LEVELS = {
    "analyst": {
        "title": "Analyst",
        "rounds": 5,
        "fee_target": 500_000,
        "description": "Your first year on the desk. Learn the ropes, support pitches, build your deal sheet.",
        "unlock": 0,
        "complexity": "Straightforward deals, supportive MDs, stable markets.",
    },
    "associate": {
        "title": "Associate",
        "rounds": 7,
        "fee_target": 2_000_000,
        "description": "Run deal execution end-to-end. Competitive processes, demanding MDs, late nights.",
        "unlock": 3000,
        "complexity": "Competitive processes, demanding MDs, covenant pressure.",
    },
    "vp": {
        "title": "VP",
        "rounds": 10,
        "fee_target": 5_000_000,
        "description": "Manage client relationships, win mandates, navigate politics. The stakes are real.",
        "unlock": 8000,
        "complexity": "Hostile boards, regulatory risk, political dynamics, cross-border complexity.",
    },
}

EVENT_CARDS = [
    {"name": "Tech IPO Frenzy", "effect": "A wave of tech IPOs floods the market. ECM desks are slammed — fees are fat but competition is fierce.", "modifier": 1.25, "sectors": ["software"]},
    {"name": "Fed Rate Hike", "effect": "Interest rates jump 50bps. LBO financing dries up, but distressed M&A picks up.", "modifier": 0.85, "sectors": []},
    {"name": "Cross-Border Bidding War", "effect": "A European strategic buyer is competing with a US PE fund. Your client is caught in the middle.", "modifier": 1.15, "sectors": []},
    {"name": "Supply Chain Disruption", "effect": "Industrial clients face margin pressure. Several deals get re-priced or pulled.", "modifier": 0.9, "sectors": ["industrials"]},
    {"name": "ESG Scrutiny", "effect": "Activist investors target a client's ESG record. Due diligence scope expands significantly.", "modifier": 1.0, "sectors": []},
    {"name": "Talent War", "effect": "A rival bank is poaching your best analysts with 30% bumps. Team morale is shaky.", "modifier": 1.0, "sectors": []},
    {"name": "SPAC De-SPAC Wave", "effect": "Several de-SPAC targets need restructuring advice. Unusual but lucrative mandates appear.", "modifier": 1.1, "sectors": []},
    {"name": "Regulatory Block", "effect": "Antitrust regulators threaten to block a major deal. Your client needs creative restructuring.", "modifier": 0.95, "sectors": []},
    {"name": "Activist Raid", "effect": "A hostile activist takes a 9% stake in your client. Poison pill defense or engagement?", "modifier": 1.0, "sectors": []},
    {"name": "Accounting Restatement", "effect": "A target company restates two years of earnings. The deal is in jeopardy.", "modifier": 0.8, "sectors": []},
    {"name": "IPO Window Opens", "effect": "Market conditions are perfect for IPOs. Several clients want to go public simultaneously.", "modifier": 1.2, "sectors": []},
    {"name": "Currency Volatility", "effect": "EUR/USD swings 8% in a month. Cross-border deal valuations are in flux.", "modifier": 0.95, "sectors": []},
]

STAGES = [
    "Pitch & Origination",
    "Analysis & Structuring",
    "Due Diligence",
    "Negotiation & Close",
    "Post-Close & League Table",
]

NPC_SELL_SIDE = {
    "firm": "Apex Capital Partners",
    "characters": [
        {"name": "Victoria Hale", "role": "Managing Partner", "trait": "Gatekeeper — controls deal flow"},
        {"name": "Marcus Reynolds", "role": "LevFin Director", "trait": "Aggressive structurer"},
        {"name": "Sophie Laurent", "role": "ECM Associate", "trait": "Market timing expert"},
    ],
}

NPC_BUY_SIDE = {
    "firm": "Blackstone Ridge Capital",
    "characters": [
        {"name": "Tom Blackwell", "role": "Senior Partner", "trait": "Old-school dealmaker"},
        {"name": "Isabella Morales", "role": "Principal", "trait": "Sharp negotiator"},
        {"name": "Kevin Park", "role": "Deal Sourcing VP", "trait": "Relentless networker"},
    ],
}

NPC_CORPORATE = {
    "firm": "Horizon Dynamics",
    "characters": [
        {"name": "Elena Petrova", "role": "Corp Dev VP", "trait": "Ex-banker, knows both sides"},
        {"name": "Ryan Kessler", "role": "M&A Director", "trait": "Process-driven, by-the-book"},
        {"name": "Jamal Wright", "role": "Business Development", "trait": "Ambitious empire-builder"},
    ],
}


@dataclass
class GameState:
    character: str = ""
    character_name: str = ""
    player_name: str = "Player"
    level: str = "analyst"
    round: int = 0
    stage_idx: int = 0
    capital: int = 0
    knowledge: int = 0
    network: int = 0
    reputation: int = 0
    deals_screened: int = 0
    deals_closed: int = 0
    deals_advised: int = 0
    fees_earned: int = 0
    mandates_won: int = 0
    special_power_used: bool = False
    events_history: list = field(default_factory=list)
    deal_pipeline: list = field(default_factory=list)
    active_mandates: list = field(default_factory=list)
    total_rounds: int = 5
    game_over: bool = False
    score: int = 0

    def current_stage(self) -> str:
        if self.stage_idx < len(STAGES):
            return STAGES[self.stage_idx]
        return "End of Round"

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def new_game(character_key: str, level: str = "analyst", player_name: str = "Player") -> GameState:
    char = CHARACTERS[character_key]
    lvl = LEVELS[level]
    return GameState(
        character=character_key,
        character_name=char["name"],
        player_name=player_name,
        level=level,
        round=1,
        stage_idx=0,
        capital=char["start_capital"],
        knowledge=char["start_knowledge"],
        network=char["start_network"],
        reputation=char["start_reputation"],
        total_rounds=lvl["rounds"],
    )


def load_deal_pipeline(limit: int = 40) -> list[dict]:
    """Load real companies from the database for the advisory pipeline."""
    from utils.database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT name, hq_city, country, sector, sub_sector, "
                f"revenue_ltm, ebitda_ltm, enterprise_value, ask_multiple, "
                f"employees, founded_year, ownership, description "
                f"FROM {DB_SCHEMA}.companies "
                f"WHERE revenue_ltm > 0 AND ebitda_ltm > 0 "
                f"ORDER BY random() LIMIT %s",
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return [
        {
            "name": r["name"],
            "city": r["hq_city"] or "",
            "country": r["country"] or "LT",
            "sector": (r["sector"] or "").replace("_", " ").title(),
            "sub_sector": (r["sub_sector"] or "").replace("_", " ").title(),
            "revenue": round(float(r["revenue_ltm"] or 0)),
            "ebitda": round(float(r["ebitda_ltm"] or 0)),
            "ev": round(float(r["enterprise_value"] or 0)),
            "multiple": round(float(r["ask_multiple"] or 0), 1),
            "employees": r["employees"] or 0,
            "founded": r["founded_year"] or 0,
            "ownership": (r["ownership"] or "").replace("_", " "),
            "description": (r["description"] or "")[:200],
        }
        for r in rows
    ]


def draw_event() -> dict:
    return random.choice(EVENT_CARDS)


def format_status(state: GameState) -> str:
    char = CHARACTERS.get(state.character, {})
    lvl = LEVELS.get(state.level, {})
    icon = char.get("icon", "")
    lines = [
        f"**Round {state.round}/{state.total_rounds}** | Stage: *{state.current_stage()}* | Level: {lvl.get('title', '')}",
        f"{icon} **{state.character_name}** — {char.get('title', '')} ({state.player_name})",
        f"${state.fees_earned:,} fees earned | {state.knowledge} knowledge | {state.network} network | {state.reputation} reputation",
        f"Mandates: {state.mandates_won} won | Deals: {state.deals_screened} screened, {state.deals_closed} closed, {state.deals_advised} advised",
    ]
    if state.active_mandates:
        lines.append(f"Active mandates: {', '.join(m.get('name', '?') for m in state.active_mandates)}")
    if not state.special_power_used:
        lines.append(f"Special: *available* — {char.get('ability', '')}")
    else:
        lines.append("Special: *used this round*")
    return "\n".join(lines)


def calculate_score(state: GameState) -> int:
    return (
        state.fees_earned
        + (state.knowledge * 500)
        + (state.network * 300)
        + (state.reputation * 400)
        + (state.deals_closed * 1000)
        + (state.deals_advised * 500)
    )
