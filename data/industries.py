"""Industry page definitions for landing site.

Each industry has a slug, title, description, sub-sectors, FAQs,
and regional advisor links.
"""

ADVISORS = {
    "lt": {"label": "Meet Advisor (LT)", "url": "https://www.orion.lt"},
    "ee": {"label": "Meet Advisor (EE)", "url": "https://superia.ee"},
}

INDUSTRIES = [
    {
        "slug": "technology",
        "title": "Technology & SaaS",
        "tagline": "A modern approach to Mergers & Acquisitions",
        "hero_heading": "Investment Banking for Technology & SaaS",
        "description": (
            "Technology companies — from bootstrapped SaaS platforms to mature IT services "
            "firms — attract significant buyer interest across the Baltics and Nordics. "
            "LiquidRound connects sellers with strategic acquirers, growth-equity funds, "
            "and cross-border buyers who understand recurring-revenue models and developer "
            "ecosystems. Our AI-powered platform builds personalised buyer lists, benchmarks "
            "your valuation against sector comps, and helps you prepare a data room that "
            "speaks the language of tech M&A."
        ),
        "bullets": [
            "Personalised buyer lists spanning Baltic, Nordic, and pan-European tech acquirers",
            "SaaS-specific valuation models (ARR multiples, NRR-adjusted, Rule of 40)",
        ],
        "sub_sectors": [
            {"name": "SaaS & Cloud Platforms", "icon": "☁️", "description": "Subscription software, cloud infrastructure, PaaS/IaaS providers"},
            {"name": "IT Services & Consulting", "icon": "⚙️", "description": "Managed services, system integration, digital transformation"},
            {"name": "FinTech & InsurTech", "icon": "💳", "description": "Payments, lending platforms, digital insurance, RegTech"},
            {"name": "Cybersecurity & Data", "icon": "🔒", "description": "Security software, data analytics, privacy compliance tools"},
        ],
        "faqs": [
            {"q": "What multiples do tech companies typically sell for?", "a": "SaaS companies with strong recurring revenue often trade at 5-10x ARR, while IT services firms trade at 1-3x revenue or 8-15x EBITDA. Multiples depend heavily on growth rate, retention, and margin profile."},
            {"q": "How do you find buyers for a Baltic tech company?", "a": "We combine our Baltic company database (covering EE, LT, LV registries) with pan-European and Nordic buyer networks, PE databases, and AI-powered matching to identify strategic and financial buyers."},
            {"q": "How long does a typical tech M&A process take?", "a": "From mandate to close, most tech transactions complete in 4-8 months. Well-prepared companies with clean data rooms and clear metrics can shorten this significantly."},
            {"q": "Do I need audited financials?", "a": "Not initially. Our tools work with management accounts. However, buyers will require audited or reviewed financials during diligence, so starting the audit early is advisable."},
            {"q": "What is LiquidRound's fee structure?", "a": "We work on a success-based model — no retainers or upfront fees. Our advisory partners charge a percentage of the transaction value, aligned with your outcome."},
        ],
    },
    {
        "slug": "manufacturing",
        "title": "Manufacturing & Industrial",
        "tagline": "A modern approach to Mergers & Acquisitions",
        "hero_heading": "Investment Banking for Manufacturing & Industrial",
        "description": (
            "Baltic and Nordic manufacturers — from precision engineering to food processing "
            "— are in high demand from international trade buyers and industrial PE funds. "
            "LiquidRound helps manufacturing owners understand their market value, identify "
            "motivated acquirers, and navigate the complexities of industrial due diligence "
            "including equipment appraisals, environmental compliance, and workforce retention."
        ),
        "bullets": [
            "Buyer lists that include strategic industrials, PE platform add-ons, and family offices",
            "EBITDA-based valuations calibrated to Baltic manufacturing transaction data",
        ],
        "sub_sectors": [
            {"name": "Precision Engineering & CNC", "icon": "🔧", "description": "Metal fabrication, machining, tool and die, aerospace components"},
            {"name": "Food & Beverage Processing", "icon": "🏭", "description": "Dairy, meat, bakery, functional foods, private label manufacturing"},
            {"name": "Building Materials & Construction", "icon": "🏗️", "description": "Concrete, timber, insulation, modular construction, fit-out"},
            {"name": "Packaging & Logistics", "icon": "📦", "description": "Corrugated, plastics, warehousing, 3PL, cold chain"},
        ],
        "faqs": [
            {"q": "What drives valuation in manufacturing?", "a": "Key drivers are EBITDA margin, customer concentration, equipment age and condition, recurring/contract revenue, workforce stability, and environmental compliance. Asset-heavy businesses may also value property and equipment separately."},
            {"q": "Are Baltic manufacturers attractive to foreign buyers?", "a": "Very. EU membership, competitive labour costs, strategic location between Western Europe and Scandinavia, and strong technical education make the Baltics a magnet for manufacturing acquirers."},
            {"q": "How do you handle equipment and real estate valuations?", "a": "We work with specialist appraisers for machinery and property. Our platform integrates these into the overall enterprise valuation, distinguishing between operating and non-operating assets."},
            {"q": "What about employee retention post-acquisition?", "a": "Buyer confidence in workforce continuity is critical. We help you prepare retention plans and highlight key-person risks in the information memorandum."},
            {"q": "What is LiquidRound's fee structure?", "a": "We work on a success-based model — no retainers or upfront fees. Our advisory partners charge a percentage of the transaction value, aligned with your outcome."},
        ],
    },
    {
        "slug": "healthcare",
        "title": "Healthcare & Life Sciences",
        "tagline": "A modern approach to Mergers & Acquisitions",
        "hero_heading": "Investment Banking for Healthcare",
        "description": (
            "Healthcare businesses — from private clinics and dental chains to MedTech "
            "startups and pharmaceutical distributors — command premium valuations when "
            "positioned correctly. LiquidRound's AI-powered platform connects healthcare "
            "sellers with specialised buyers who understand regulatory environments, "
            "reimbursement models, and clinical workflows across the Baltic and Nordic markets."
        ),
        "bullets": [
            "Buyer networks spanning healthcare PE, hospital groups, and pharma corporates",
            "Regulatory-aware diligence templates for healthcare-specific compliance",
        ],
        "sub_sectors": [
            {"name": "Private Clinics & Dental", "icon": "🏥", "description": "Multi-site clinics, dental chains, specialty practices, diagnostics"},
            {"name": "MedTech & Digital Health", "icon": "💊", "description": "Medical devices, telemedicine, health AI, patient management software"},
            {"name": "Pharma & Distribution", "icon": "🧬", "description": "Generic manufacturing, wholesale distribution, specialty pharma, CRO/CMO"},
            {"name": "Veterinary & Animal Health", "icon": "🐾", "description": "Vet clinic chains, animal pharma, pet care, agri-health"},
        ],
        "faqs": [
            {"q": "What multiples do healthcare businesses trade at?", "a": "Healthcare services typically trade at 8-15x EBITDA depending on scale, payer mix, and regulatory moat. MedTech and digital health companies with SaaS revenue can command higher multiples."},
            {"q": "How do regulatory approvals affect the deal?", "a": "Regulatory compliance (CE marks, medical device registration, pharmacy licences) is a key value driver. Clean regulatory history accelerates diligence and supports premium pricing."},
            {"q": "Are there specific buyer types for Baltic healthcare?", "a": "Yes — Nordic hospital groups expanding south, pan-European PE platforms rolling up clinics, and MedTech strategics seeking Baltic development centres are all active."},
            {"q": "How do you handle patient data and GDPR in diligence?", "a": "We ensure data room setup follows GDPR best practices for health data. Patient records never leave the provider; diligence focuses on aggregate metrics and anonymised data."},
            {"q": "What is LiquidRound's fee structure?", "a": "We work on a success-based model — no retainers or upfront fees. Our advisory partners charge a percentage of the transaction value, aligned with your outcome."},
        ],
    },
    {
        "slug": "business-services",
        "title": "Business Services",
        "tagline": "A modern approach to Mergers & Acquisitions",
        "hero_heading": "Investment Banking for Business Services",
        "description": (
            "Business services companies — from accounting and staffing firms to marketing "
            "agencies and facility managers — are prime targets for PE-backed platform "
            "strategies and strategic consolidators. LiquidRound helps services owners "
            "quantify recurring-revenue value, benchmark against peer transactions, and "
            "access buyers who are actively building multi-site services platforms across "
            "the Baltics and Nordics."
        ),
        "bullets": [
            "Tailored buyer lists including services-focused PE, Nordic consolidators, and trade buyers",
            "Recurring-revenue and contract-backlog adjusted valuations",
        ],
        "sub_sectors": [
            {"name": "Accounting & Advisory", "icon": "📊", "description": "Audit, tax, advisory, bookkeeping, payroll outsourcing"},
            {"name": "Staffing & HR Services", "icon": "👥", "description": "Temporary staffing, executive search, HR tech, PEO/EOR"},
            {"name": "Marketing & Creative", "icon": "📢", "description": "Digital agencies, PR, branding, media buying, content production"},
            {"name": "Facilities & Field Services", "icon": "🔑", "description": "Commercial cleaning, property management, security, maintenance"},
        ],
        "faqs": [
            {"q": "What makes business services attractive to buyers?", "a": "Recurring revenue, long-term contracts, low capex, and scalable delivery models. Buyers love predictable cash flows, especially when supported by multi-year client relationships."},
            {"q": "How are services firms typically valued?", "a": "Most trade at 5-10x EBITDA, with premium multiples for firms with strong recurring revenue, diverse client bases, and limited key-person risk. Staffing firms are valued on gross profit multiples."},
            {"q": "What about key-person risk?", "a": "It's the #1 concern for services buyers. We help you document processes, formalise client relationships, and build a management team story that gives buyers confidence in continuity."},
            {"q": "Can I sell a minority stake instead of 100%?", "a": "Yes. Many PE buyers prefer majority stakes with management rollover, and some offer minority growth investments. Our platform matches you with the right structure."},
            {"q": "What is LiquidRound's fee structure?", "a": "We work on a success-based model — no retainers or upfront fees. Our advisory partners charge a percentage of the transaction value, aligned with your outcome."},
        ],
    },
]

INDUSTRIES_BY_SLUG = {ind["slug"]: ind for ind in INDUSTRIES}
