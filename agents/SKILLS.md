# Scoring Agent — Skills Reference

The scoring agent (`agents/scoring_agent.py`) evaluates M&A opportunities across 7 weighted synergy dimensions. It can operate in multiple modes depending on available context.

## Skills

### 1. Buyer-Target Match Scoring
**Trigger:** `score buyer:X target:Y`
**Input:** Buyer profile, target company, optional deal context
**Output:** Composite score (0-100), 7 dimension scores, recommendation, risks, next steps

### 2. Document-Based Buyer Matching
**Trigger:** `score doc:<filename>` or upload a document then `score`
**Input:** Parsed document content (CIM, pitch deck, financial model)
**Process:**
  1. Extract company profile, financials, and strategic positioning from document
  2. Identify the company's sector, size, growth profile, and competitive moat
  3. Generate 5-8 ideal buyer profiles (strategic + financial)
  4. Score each buyer match across all 7 dimensions
  5. Rank by composite score and return top matches with reasoning
**Output:** Ranked buyer matches with per-dimension scores and rationale

### 3. Research-Enhanced Scoring
**Trigger:** `score buyer:X target:Y research:true`
**Input:** Buyer + target + live EXA/Tavily research data
**Process:**
  1. Run deep research on both buyer and target
  2. Feed research snippets into scoring context
  3. Score with market-aware reasoning
**Output:** Same as match scoring but with research-backed evidence

## Scoring Dimensions

| # | Dimension | Weight | What it Measures |
|---|-----------|--------|-----------------|
| 1 | Revenue Synergies | 20% | Cross-sell, market expansion, pricing power |
| 2 | Cost Synergies | 20% | Operational overlap, procurement, headcount |
| 3 | Strategic Fit | 15% | Vision alignment, moat, product synergy |
| 4 | Cultural Fit | 10% | Management style, org structure, geography |
| 5 | Financial Health | 15% | Balance sheet, cash flow, debt capacity |
| 6 | Integration Risk | 10% | IT complexity, regulatory, retention (inverted: 10=LOW risk) |
| 7 | Market Timing | 10% | Sector cycle, macro, interest rates |

## Recommendation Thresholds

- **STRONG BUY** (>=80): Exceptional match across most dimensions
- **PROCEED** (65-79): Strong match with manageable gaps
- **CAUTIOUS** (50-64): Mixed signals, significant DD required
- **PASS** (<50): Fundamental misalignment

## Prompt File
`prompts/scoring.md` — full system prompt with rubrics and guidelines

## Example Invocations
```
score buyer:Salesforce target:HubSpot
score doc:EstateGuru-2024-10-01.pdf
score buyer:ThomaBravo target:Coupa context:enterprise SaaS consolidation
```
