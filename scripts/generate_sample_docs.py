"""
Generate synthetic M&A demo documents for LiquidRound.
Creates a pitch deck and term sheet PDF in docs-data/.
"""
from fpdf import FPDF
from pathlib import Path

DOCS_DATA = Path(__file__).parent.parent / "docs-data"

# Colors
NAVY = (20, 40, 80)
BLUE = (37, 99, 235)
DARK = (30, 30, 30)
GRAY = (100, 100, 100)
LIGHT_GRAY = (200, 200, 200)
WHITE = (255, 255, 255)
GREEN = (22, 163, 74)


class PitchDeckPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(*GRAY)
            self.cell(0, 4, "CONFIDENTIAL - NovaTech Solutions OU", align="L")
            self.cell(0, 4, f"Page {self.page_no()}", align="R")
            self.ln(8)

    def section_title(self, text):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*NAVY)
        self.cell(0, 12, text)
        self.ln(14)

    def subtitle(self, text):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*BLUE)
        self.cell(0, 8, text)
        self.ln(10)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        x = self.get_x()
        self.cell(8, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def metric_row(self, label, value):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.cell(70, 7, label)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.cell(0, 7, value)
        self.ln(7)

    def divider(self):
        self.set_draw_color(*LIGHT_GRAY)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def generate(self):
        self.set_auto_page_break(auto=True, margin=20)

        # Page 1: Cover
        self.add_page()
        self.ln(50)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(*NAVY)
        self.cell(0, 15, "NovaTech Solutions", align="C")
        self.ln(18)
        self.set_font("Helvetica", "", 14)
        self.set_text_color(*GRAY)
        self.cell(0, 8, "Confidential Investment Presentation", align="C")
        self.ln(10)
        self.cell(0, 8, "Q1 2026", align="C")
        self.ln(30)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, "AI-Powered Supply Chain Visibility Platform", align="C")
        self.ln(8)
        self.cell(0, 6, "Tallinn, Estonia  |  Founded 2018  |  120 Employees", align="C")
        self.ln(30)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.5)
        self.line(70, self.get_y(), self.w - 70, self.get_y())
        self.ln(8)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 5, "This document is strictly confidential and intended solely for the recipient.", align="C")
        self.ln(5)
        self.cell(0, 5, "Do not distribute without prior written consent of NovaTech Solutions OU.", align="C")

        # Page 2: Executive Summary
        self.add_page()
        self.section_title("Executive Summary")
        self.body_text(
            "NovaTech Solutions is a high-growth B2B SaaS company providing AI-powered supply chain "
            "visibility to mid-market and enterprise logistics operators across Northern Europe. The company "
            "has grown revenue from EUR 3.2M in 2022 to EUR 18M ARR in 2025, representing a 78% CAGR."
        )
        self.subtitle("Investment Highlights")
        self.bullet("EUR 18M ARR with 85% gross margins and clear path to profitability in H2 2026")
        self.bullet("220 enterprise customers with 130% net dollar retention and 95% gross retention")
        self.bullet("Category-leading AI platform for predictive ETAs, supplier risk scoring, and carbon tracking")
        self.bullet("Strong position in Baltic/Nordic markets with expansion underway into DACH and UK")
        self.bullet("Experienced management team with prior exits in logistics technology")
        self.ln(3)
        self.subtitle("Transaction Overview")
        self.body_text(
            "NovaTech is seeking a strategic acquirer or growth equity partner to accelerate international "
            "expansion and product development. The company is open to a full acquisition (100% share sale) "
            "or a significant minority investment (30-40%). Indicative valuation range: EUR 120-150M (7-8x ARR)."
        )

        # Page 3: Company Overview
        self.add_page()
        self.section_title("Company Overview")
        self.metric_row("Legal Entity:", "NovaTech Solutions OU")
        self.metric_row("Headquarters:", "Tallinn, Estonia")
        self.metric_row("Founded:", "2018")
        self.metric_row("Employees:", "120 (85 engineering, 20 sales, 15 G&A)")
        self.metric_row("Offices:", "Tallinn (HQ), Riga, Helsinki, Berlin (sales)")
        self.metric_row("CEO:", "Kaido Tamm (ex-VP Engineering, Cleveron)")
        self.metric_row("CTO:", "Anna Rebane (ex-Lead Architect, Bolt)")
        self.divider()
        self.subtitle("Business Model")
        self.body_text(
            "NovaTech operates a pure SaaS model with annual subscriptions. Revenue is split between "
            "platform fees (70%) and premium AI modules (30%). The platform processes 2.5M shipment "
            "tracking events daily across 45 countries, providing real-time visibility, predictive ETAs "
            "with 94% accuracy, and automated supplier performance scoring."
        )
        self.subtitle("Key Customers")
        self.bullet("DSV Panalpina (logistics) - EUR 420K ACV, live since 2021")
        self.bullet("Maersk Line (maritime) - EUR 380K ACV, expanded 2024")
        self.bullet("Omniva (postal/logistics) - EUR 210K ACV, Baltic anchor")
        self.bullet("Schenker DB (freight) - EUR 350K ACV, DACH entry point")
        self.bullet("Tallink (shipping) - EUR 180K ACV, cross-sell into cruise logistics")

        # Page 4: Market Opportunity
        self.add_page()
        self.section_title("Market Opportunity")
        self.subtitle("Supply Chain Visibility Software Market")
        self.body_text(
            "The global supply chain visibility market is projected to reach USD 42B by 2028, growing at "
            "15.2% CAGR from USD 21B in 2024 (Gartner). Post-COVID supply chain disruptions have made "
            "real-time tracking and predictive analytics a top-3 priority for logistics executives."
        )
        self.metric_row("TAM (Global):", "USD 42B (2028E)")
        self.metric_row("SAM (Europe):", "USD 8.5B")
        self.metric_row("SOM (Nordics + Baltic + DACH):", "USD 1.2B")
        self.divider()
        self.subtitle("Market Drivers")
        self.bullet("Regulatory pressure: EU Supply Chain Due Diligence Directive (CSDDD) effective 2026")
        self.bullet("ESG reporting: mandatory Scope 3 carbon tracking for supply chains")
        self.bullet("Disruption fatigue: 78% of shippers cite visibility as top investment priority (McKinsey 2025)")
        self.bullet("AI readiness: predictive models now outperform rule-based systems by 3x on ETA accuracy")

        # Page 5: Product & Technology
        self.add_page()
        self.section_title("Product & Technology")
        self.subtitle("Platform Modules")
        self.bullet("Shipment Tracker: Real-time multimodal tracking (ocean, air, road, rail) across 45 countries")
        self.bullet("Predictive ETA Engine: ML model with 94% accuracy, 3.2hr avg improvement over carrier ETAs")
        self.bullet("Supplier Risk Score: AI-driven scoring of 12,000+ suppliers on reliability, ESG, financial health")
        self.bullet("Carbon Calculator: Scope 3 emissions tracking per shipment, EU taxonomy compliant")
        self.bullet("API Marketplace: 180+ carrier integrations, REST + webhook, avg 99.7% uptime")
        self.ln(3)
        self.subtitle("Technology Stack")
        self.body_text(
            "Cloud-native architecture on AWS (eu-north-1), microservices in Python and Go, "
            "PostgreSQL + TimescaleDB for time-series data, Kafka for event streaming, "
            "custom ML models (PyTorch) for ETA prediction and anomaly detection."
        )
        self.subtitle("IP & Competitive Moat")
        self.bullet("3 patent applications (predictive routing, anomaly detection, carbon attribution)")
        self.bullet("Proprietary training dataset: 4.2B historical shipment events (2019-2025)")
        self.bullet("Average integration time: 2.3 weeks (vs. 8-12 weeks for competitors)")

        # Page 6: Financial Highlights
        self.add_page()
        self.section_title("Financial Highlights")
        self.subtitle("Revenue Growth (EUR M)")
        self.ln(2)
        # Simple table
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        cols = ["", "2022", "2023", "2024", "2025", "2026E"]
        w = 30
        for c in cols:
            self.cell(w, 7, c, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 9)
        rows = [
            ("ARR", "3.2", "6.8", "12.1", "18.0", "28.0"),
            ("Revenue", "2.8", "5.9", "10.5", "16.2", "25.5"),
            ("Gross Profit", "2.3", "4.9", "8.8", "13.8", "22.1"),
            ("Gross Margin", "82%", "83%", "84%", "85%", "87%"),
            ("EBITDA", "-1.8", "-2.1", "-1.4", "-0.8", "1.2"),
            ("EBITDA Margin", "-64%", "-36%", "-13%", "-5%", "5%"),
        ]
        for row in rows:
            for i, v in enumerate(row):
                self.set_font("Helvetica", "B" if i == 0 else "", 9)
                self.cell(w, 7, v, border=1, align="C" if i > 0 else "L")
            self.ln()
        self.ln(5)
        self.subtitle("Key Financial Metrics")
        self.metric_row("Cash & Equivalents:", "EUR 6.2M (Dec 2025)")
        self.metric_row("Total Funding Raised:", "EUR 22M (Seed + Series A + B)")
        self.metric_row("Monthly Burn Rate:", "EUR 180K (declining)")
        self.metric_row("Runway:", "34 months at current burn")

        # Page 7: Key Metrics
        self.add_page()
        self.section_title("Key Operating Metrics")
        self.ln(2)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        cols2 = ["Metric", "2023", "2024", "2025", "Target 2026"]
        widths = [55, 30, 30, 30, 35]
        for c, w2 in zip(cols2, widths):
            self.cell(w2, 7, c, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 9)
        metrics = [
            ("Enterprise Customers", "95", "158", "220", "320"),
            ("Net Dollar Retention", "118%", "125%", "130%", "135%"),
            ("Gross Retention", "92%", "94%", "95%", "96%"),
            ("Avg Contract Value (EUR K)", "72", "77", "82", "88"),
            ("CAC Payback (months)", "18", "16", "14", "12"),
            ("LTV/CAC Ratio", "3.8x", "4.5x", "5.2x", "6.0x"),
            ("NPS Score", "52", "58", "64", "70"),
            ("Shipments Tracked (M/day)", "0.8", "1.5", "2.5", "4.0"),
        ]
        for row in metrics:
            for i, (v, w2) in enumerate(zip(row, widths)):
                self.set_font("Helvetica", "B" if i == 0 else "", 9)
                self.cell(w2, 7, v, border=1, align="C" if i > 0 else "L")
            self.ln()

        # Page 8: Competitive Landscape
        self.add_page()
        self.section_title("Competitive Landscape")
        self.body_text(
            "NovaTech competes in the supply chain visibility segment against both large incumbents "
            "and venture-backed challengers. Our differentiation is AI-first architecture, European "
            "data residency, and deep Baltic/Nordic market penetration."
        )
        self.ln(3)
        self.subtitle("Competitive Positioning")
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        cols3 = ["Company", "HQ", "Focus", "Strength", "Weakness vs NT"]
        widths3 = [32, 22, 38, 40, 48]
        for c, w3 in zip(cols3, widths3):
            self.cell(w3, 7, c, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 8)
        comps = [
            ("FourKites", "US", "Real-time visibility", "Scale, 1000+ clients", "No EU data residency"),
            ("project44", "US", "Multimodal tracking", "Carrier network", "Limited AI/ML depth"),
            ("Overhaul", "US", "Risk & compliance", "Security focus", "No predictive ETA"),
            ("Descartes", "CA", "Logistics IT suite", "Breadth of tools", "Legacy architecture"),
            ("NovaTech", "EE", "AI visibility + ESG", "AI, EU compliant", "Smaller scale (today)"),
        ]
        for row in comps:
            for v, w3 in zip(row, widths3):
                self.cell(w3, 7, v, border=1, align="C" if v == row[0] else "L")
            self.ln()

        # Page 9: Growth Strategy
        self.add_page()
        self.section_title("Growth Strategy 2026-2028")
        self.subtitle("1. Geographic Expansion")
        self.bullet("DACH market entry: Berlin office opened Q4 2025, 3 enterprise pilots signed")
        self.bullet("UK market: targeting Q2 2026 launch, post-Brexit customs module as wedge product")
        self.bullet("Benelux: partnership with Port of Rotterdam for IoT data integration")
        self.ln(2)
        self.subtitle("2. Product Expansion")
        self.bullet("Customs & Trade Compliance module (EUR 3M revenue potential by 2027)")
        self.bullet("Carbon Attribution Engine for EU CSDDD compliance (mandatory 2026)")
        self.bullet("Warehouse Visibility extension (partnership with AutoStore)")
        self.ln(2)
        self.subtitle("3. Revenue Targets")
        self.metric_row("2026E ARR:", "EUR 28M (+56% YoY)")
        self.metric_row("2027E ARR:", "EUR 42M (+50% YoY)")
        self.metric_row("2028E ARR:", "EUR 58M (+38% YoY)")
        self.metric_row("2028E EBITDA Margin:", "18-22%")

        # Page 10: Transaction Summary
        self.add_page()
        self.section_title("Transaction Summary")
        self.subtitle("Transaction Structure")
        self.body_text(
            "NovaTech Solutions is seeking a strategic partner to accelerate its next phase of growth. "
            "The company is open to both full acquisition and significant minority investment structures."
        )
        self.ln(2)
        self.metric_row("Transaction Type:", "100% share acquisition or 30-40% minority stake")
        self.metric_row("Indicative Valuation:", "EUR 120-150M enterprise value (7-8x 2025 ARR)")
        self.metric_row("Consideration:", "Cash + equity rollover (for minority)")
        self.metric_row("Management:", "CEO and CTO committed to 24-month retention")
        self.metric_row("Exclusivity:", "90-day exclusivity upon LOI signing")
        self.metric_row("Timeline:", "Target LOI by Q2 2026, closing Q4 2026")
        self.divider()
        self.subtitle("Ideal Buyer Profile")
        self.bullet("Global logistics technology platform seeking European market entry")
        self.bullet("Supply chain software company looking for AI/ML capabilities")
        self.bullet("Enterprise SaaS acquirer building a logistics vertical")
        self.bullet("Strategic corporate buyer in freight/logistics with digitalization mandate")
        self.ln(5)
        self.subtitle("Contact")
        self.body_text(
            "For inquiries, please contact:\n"
            "Kaido Tamm, CEO - kaido@novatech.example\n"
            "Sell-side Advisor: Nordic M&A Partners"
        )


class TermSheetPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 4, "DRAFT - FOR DISCUSSION PURPOSES ONLY - NON-BINDING", align="C")
        self.ln(8)

    def section(self, text):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*NAVY)
        self.cell(0, 10, text)
        self.ln(10)

    def term_row(self, label, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.cell(55, 7, label)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        w = self.w - self.l_margin - self.r_margin - 55
        self.multi_cell(w, 7, value)
        self.ln(2)

    def divider(self):
        self.set_draw_color(*LIGHT_GRAY)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)

    def generate(self):
        self.set_auto_page_break(auto=True, margin=20)

        # Page 1: Core Terms
        self.add_page()
        self.ln(5)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*NAVY)
        self.cell(0, 12, "Indicative Term Sheet", align="C")
        self.ln(8)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "Acquisition of NovaTech Solutions OU", align="C")
        self.ln(4)
        self.cell(0, 6, "Draft Date: March 15, 2026", align="C")
        self.ln(12)

        self.section("1. Parties")
        self.term_row("Buyer:", "[Buyer Entity TBD] (the \"Buyer\")")
        self.term_row("Seller:", "Shareholders of NovaTech Solutions OU, registry code 14567890, "
                       "registered in Tallinn, Estonia (the \"Seller\")")
        self.term_row("Target:", "NovaTech Solutions OU and its subsidiaries (the \"Company\")")
        self.divider()

        self.section("2. Transaction Structure")
        self.term_row("Type:", "Acquisition of 100% of the issued share capital of the Company")
        self.term_row("Enterprise Value:", "EUR 135,000,000 (one hundred thirty-five million euros)")
        self.term_row("Equity Value:", "Subject to customary adjustments for net debt, working capital, "
                       "and cash-like items at closing")
        self.divider()

        self.section("3. Consideration")
        self.term_row("Cash Component:", "70% - EUR 94,500,000 payable at closing")
        self.term_row("Equity Component:", "20% - EUR 27,000,000 in newly issued shares of Buyer, "
                       "subject to 12-month lock-up")
        self.term_row("Earnout:", "10% - EUR 13,500,000 contingent on Company achieving "
                       "EUR 28M ARR by December 31, 2026 and EUR 42M ARR by December 31, 2027")

        # Page 2: Conditions & DD
        self.add_page()
        self.section("4. Key Conditions")
        self.term_row("Due Diligence:", "Buyer to complete confirmatory due diligence within 60 days "
                       "of execution of this term sheet. Full data room access to be provided.")
        self.term_row("Management:", "CEO (Kaido Tamm) and CTO (Anna Rebane) to enter 24-month "
                       "employment agreements with market-rate compensation and retention bonuses.")
        self.term_row("Regulatory:", "Completion subject to merger control clearance in Estonia "
                       "(Competition Authority) and any other applicable jurisdiction.")
        self.term_row("IP Assignment:", "Confirmation that all intellectual property is fully owned "
                       "by the Company with no third-party encumbrances.")
        self.term_row("Material Adverse\nChange:", "Standard MAC clause covering material changes to "
                       "business, financial condition, or key customer relationships.")
        self.divider()

        self.section("5. Exclusivity & Timeline")
        self.term_row("Exclusivity:", "90 days from execution of this term sheet. Seller shall not "
                       "solicit, encourage, or engage in discussions with third parties.")
        self.term_row("Break Fee:", "2.5% of Enterprise Value (EUR 3,375,000) payable by either "
                       "party upon breach of exclusivity or withdrawal without cause.")
        self.term_row("Target Timeline:", "LOI execution: April 2026\n"
                       "Due diligence completion: June 2026\n"
                       "SPA execution: August 2026\n"
                       "Regulatory clearance: September 2026\n"
                       "Closing: October 2026")

        # Page 3: Governance & Legal
        self.add_page()
        self.section("6. Post-Closing Governance")
        self.term_row("Operating Model:", "Company to operate as an independent business unit within "
                       "Buyer's organization for a minimum of 12 months post-closing.")
        self.term_row("Brand:", "NovaTech brand to be retained for 24 months, with co-branding "
                       "permitted after 12 months.")
        self.term_row("Employees:", "Buyer commits to retaining at least 90% of current employees "
                       "for 12 months. No relocation of Tallinn engineering hub.")
        self.term_row("Board:", "Company board to include 2 Buyer nominees, 1 Seller nominee "
                       "(CEO), and 1 independent director for 24 months.")
        self.divider()

        self.section("7. Non-Compete & Confidentiality")
        self.term_row("Non-Compete:", "Founders and key management subject to 36-month non-compete "
                       "within supply chain SaaS and logistics visibility software, "
                       "geographic scope: EEA and United Kingdom.")
        self.term_row("Non-Solicit:", "24-month non-solicitation of Company employees and customers.")
        self.term_row("Confidentiality:", "This term sheet and all related discussions are strictly "
                       "confidential. Standard mutual NDA terms apply.")
        self.divider()

        self.section("8. General")
        self.term_row("Governing Law:", "Laws of Estonia")
        self.term_row("Dispute Resolution:", "ICC International Court of Arbitration, seat in Tallinn")
        self.term_row("Costs:", "Each party bears its own costs. Buyer to reimburse Seller's "
                       "reasonable advisory fees (capped at EUR 500,000) upon successful closing.")
        self.term_row("Binding:", "This term sheet is non-binding except for Sections 5 (Exclusivity), "
                       "7 (Non-Compete/Confidentiality), and 8 (General).")
        self.ln(10)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK)
        self.cell(0, 7, "ACKNOWLEDGED AND AGREED:")
        self.ln(12)
        self.set_font("Helvetica", "", 10)
        self.cell(85, 7, "For and on behalf of [Buyer]:")
        self.cell(0, 7, "For and on behalf of NovaTech Solutions OU:")
        self.ln(15)
        self.cell(85, 7, "________________________________")
        self.cell(0, 7, "________________________________")
        self.ln(6)
        self.cell(85, 7, "Name:")
        self.cell(0, 7, "Name: Kaido Tamm, CEO")
        self.ln(6)
        self.cell(85, 7, "Date:")
        self.cell(0, 7, "Date:")


def main():
    DOCS_DATA.mkdir(exist_ok=True)

    pitch = PitchDeckPDF()
    pitch.generate()
    pitch.output(str(DOCS_DATA / "NovaTech-Pitch-Deck.pdf"))
    print(f"Created: {DOCS_DATA / 'NovaTech-Pitch-Deck.pdf'}")

    term = TermSheetPDF()
    term.generate()
    term.output(str(DOCS_DATA / "NovaTech-TermSheet-Draft.pdf"))
    print(f"Created: {DOCS_DATA / 'NovaTech-TermSheet-Draft.pdf'}")


if __name__ == "__main__":
    main()
