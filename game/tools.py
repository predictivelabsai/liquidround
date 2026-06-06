"""Game state mutation tools — called by the LangGraph game master agent.

Each tool receives game state via closure and mutates it in place.
Tools return confirmation text that the agent weaves into its narrative.
"""

from __future__ import annotations

from langchain_core.tools import tool

from game.engine import GameState, STAGES, LEVELS, CHARACTERS, calculate_score


_FEE_CHANGE_MAX = 5_000_000
_STAT_CHANGE_MIN = -3
_STAT_CHANGE_MAX = 3


def build_game_tools(state: GameState):
    """Build tools bound to a specific game state instance."""

    @tool
    def advance_stage() -> str:
        """Advance the game to the next stage. Call when the current stage's
        action is resolved. Stages cycle through:
        Pitch & Origination -> Analysis & Structuring -> Due Diligence ->
        Negotiation & Close -> Post-Close & League Table.
        After the last stage, a new round begins."""
        state.stage_idx += 1
        if state.stage_idx >= len(STAGES):
            state.stage_idx = 0
            state.round += 1
            state.special_power_used = False
            if state.round > state.total_rounds:
                state.game_over = True
                state.score = calculate_score(state)
                return (
                    f"GAME OVER! Final round complete. "
                    f"Score: {state.score:,}. "
                    f"Fees earned: ${state.fees_earned:,}. "
                    f"Deals closed: {state.deals_closed}."
                )
            return (
                f"New round! Now in Round {state.round}/{state.total_rounds}, "
                f"Stage: {state.current_stage()}. "
                f"Special power is available again."
            )
        return (
            f"Advanced to {state.current_stage()} "
            f"(Round {state.round}/{state.total_rounds})."
        )

    @tool
    def adjust_resources(
        knowledge_change: int = 0,
        network_change: int = 0,
        reputation_change: int = 0,
        reason: str = "",
    ) -> str:
        """Adjust the player's resources based on their action outcome.
        Use positive values for gains, negative for costs/losses.
        Always provide a reason explaining why resources changed.

        Guardrails: each stat clamped to [-3, +3] per call.
        Stats cannot drop below 0."""
        know = max(_STAT_CHANGE_MIN, min(_STAT_CHANGE_MAX, knowledge_change))
        net = max(_STAT_CHANGE_MIN, min(_STAT_CHANGE_MAX, network_change))
        rep = max(_STAT_CHANGE_MIN, min(_STAT_CHANGE_MAX, reputation_change))

        state.knowledge = max(0, state.knowledge + know)
        state.network = max(0, state.network + net)
        state.reputation = max(0, state.reputation + rep)

        parts = []
        for label, val in [("knowledge", know), ("network", net), ("reputation", rep)]:
            if val > 0:
                parts.append(f"{label} +{val}")
            elif val < 0:
                parts.append(f"{label} {val}")

        change_str = ", ".join(parts) if parts else "no change"
        return (
            f"Resources updated ({change_str}). "
            f"Reason: {reason}. "
            f"Current: {state.knowledge} knowledge, "
            f"{state.network} network, {state.reputation} reputation."
        )

    @tool
    def win_mandate(
        company_name: str,
        country: str,
        sector: str,
        deal_value: int,
        deal_type: str = "M&A advisory",
        revenue: int = 0,
        ebitda: int = 0,
    ) -> str:
        """Record winning an advisory mandate from a client.
        The player's bank is now advising on this deal.
        Deal types: M&A advisory, IPO underwriting, debt advisory, restructuring."""
        mandate = {
            "name": company_name,
            "country": country,
            "sector": sector,
            "deal_value": deal_value,
            "deal_type": deal_type,
            "revenue": revenue,
            "ebitda": ebitda,
        }
        state.active_mandates.append(mandate)
        state.mandates_won += 1
        return (
            f"Mandate won! Now advising {company_name} ({country}, {sector}) "
            f"on {deal_type}. Deal value: ${deal_value:,}. "
            f"Active mandates: {len(state.active_mandates)}. "
            f"Total mandates won: {state.mandates_won}."
        )

    @tool
    def close_deal(
        company_name: str,
        deal_value: int,
        fee_percentage: float = 1.5,
    ) -> str:
        """Close a deal the player is advising on. Calculates and awards fees.
        Fee percentage should be realistic: 1-2% for M&A, 3-7% for IPO.
        Removes the mandate from active list."""
        target = None
        for i, m in enumerate(state.active_mandates):
            if m["name"].lower() == company_name.lower():
                target = (i, m)
                break
        if not target:
            return (
                f"No active mandate for '{company_name}'. "
                f"Active mandates: {[m['name'] for m in state.active_mandates]}"
            )

        idx, mandate = target
        fee = int(deal_value * fee_percentage / 100)
        fee = min(fee, _FEE_CHANGE_MAX)
        state.fees_earned += fee
        state.capital += fee
        state.deals_closed += 1
        state.active_mandates.pop(idx)

        return (
            f"DEAL CLOSED! {company_name} — ${deal_value:,} deal value. "
            f"Fee: ${fee:,} ({fee_percentage}%). "
            f"Total fees earned: ${state.fees_earned:,}. "
            f"Active mandates remaining: {len(state.active_mandates)}."
        )

    @tool
    def collect_fee(
        amount: int,
        source: str = "advisory retainer",
    ) -> str:
        """Collect advisory fees outside of a deal closing — retainers,
        monthly fees, success bonuses, etc. Amount in dollars."""
        amount = max(0, min(amount, _FEE_CHANGE_MAX))
        state.fees_earned += amount
        state.capital += amount
        return (
            f"Fee collected: ${amount:,} ({source}). "
            f"Total fees earned: ${state.fees_earned:,}."
        )

    @tool
    def screen_deal(
        company_name: str,
        country: str,
        sector: str,
        revenue: int,
        ebitda: int,
        verdict: str = "promising",
    ) -> str:
        """Record that the player screened/evaluated a potential mandate.
        Verdict should be: promising, pass, needs-more-diligence."""
        state.deals_screened += 1
        state.deals_advised += 1
        return (
            f"Screened {company_name} ({country}, {sector}): "
            f"${revenue:,} revenue, ${ebitda:,} EBITDA. "
            f"Verdict: {verdict}. "
            f"Total deals screened: {state.deals_screened}."
        )

    @tool
    def use_special_power() -> str:
        """Activate the character's special ability for this round.
        Each character has a unique power usable once per round.
        The power resets when a new round begins."""
        if state.special_power_used:
            return (
                "Special power already used this round! "
                "It will reset at the start of the next round."
            )
        char = CHARACTERS.get(state.character, {})
        state.special_power_used = True
        return (
            f"Special power activated: {char.get('ability', 'unknown')}. "
            f"This ability is now spent for Round {state.round}."
        )

    @tool
    def get_game_status() -> str:
        """Get the current game status — resources, mandates, round/stage info.
        Call this to check the player's current position before making decisions."""
        from game.engine import format_status
        return format_status(state)

    @tool
    def browse_pipeline(sector: str = "", min_revenue: int = 0, max_ev: int = 0) -> str:
        """Browse the deal pipeline for potential advisory clients matching criteria.
        Returns up to 8 companies. Filter by sector, minimum revenue, or max EV.
        These are REAL companies — use their exact names and financials.
        Frame them as potential advisory mandates."""
        matches = state.deal_pipeline
        if sector:
            matches = [c for c in matches if sector.lower() in c["sector"].lower()]
        if min_revenue:
            matches = [c for c in matches if c["revenue"] >= min_revenue]
        if max_ev and max_ev > 0:
            matches = [c for c in matches if c["ev"] <= max_ev]
        matches = matches[:8]
        if not matches:
            return "No companies match those criteria. Try broadening your search."
        lines = []
        for c in matches:
            margin = round(c["ebitda"] / max(1, c["revenue"]) * 100, 1)
            lines.append(
                f"* **{c['name']}** ({c['city']}, {c['country']})\n"
                f"  {c['sector']}{(' / ' + c['sub_sector']) if c['sub_sector'] else ''} | "
                f"${c['revenue']/1e6:.1f}M rev | ${c['ebitda']/1e6:.1f}M EBITDA ({margin}% margin) | "
                f"EV ${c['ev']/1e6:.0f}M ({c['multiple']}x) | "
                f"{c['employees']} employees | {c['ownership']}\n"
                f"  {c['description']}"
            )
        return f"Pipeline ({len(matches)} matches):\n\n" + "\n\n".join(lines)

    return [
        advance_stage,
        adjust_resources,
        win_mandate,
        close_deal,
        collect_fee,
        screen_deal,
        use_special_power,
        get_game_status,
        browse_pipeline,
    ]
