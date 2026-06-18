"""Internationalization for LiquidRound — EN, ET (Estonian), LT (Lithuanian), LV (Latvian).

Pattern ported from pehero: session-based language, `t(key, lang)` lookup,
flag-emoji dropdown in nav. Fallback: lang → EN → key.
"""
from __future__ import annotations

from typing import Any

DEFAULT_LANG = "en"

LANGUAGES: dict[str, dict[str, str]] = {
    "en": {"name": "English",    "flag": "🇬🇧", "native": "English"},
    "et": {"name": "Estonian",   "flag": "🇪🇪", "native": "Eesti"},
    "lt": {"name": "Lithuanian", "flag": "🇱🇹", "native": "Lietuvių"},
    "lv": {"name": "Latvian",   "flag": "🇱🇻", "native": "Latviešu"},
}

SUPPORTED_LANGS = tuple(LANGUAGES.keys())

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Navigation ──
    "nav_platform":     {"en": "Platform",    "et": "Platvorm",     "lt": "Platforma",    "lv": "Platforma"},
    "nav_agents":       {"en": "ECM Squad",   "et": "ECM meeskond", "lt": "ECM komanda",  "lv": "ECM komanda"},
    "nav_tools":        {"en": "Tools",       "et": "Tööriistad",   "lt": "Įrankiai",     "lv": "Rīki"},
    "nav_industries":   {"en": "Industries",  "et": "Tööstused",    "lt": "Pramonės",     "lv": "Nozares"},
    "nav_pricing":      {"en": "Pricing",     "et": "Hinnakiri",    "lt": "Kainos",       "lv": "Cenas"},
    "nav_sign_in":      {"en": "Sign in",     "et": "Logi sisse",   "lt": "Prisijungti",  "lv": "Pieslēgties"},

    # ── Landing hero ──
    "hero_eyebrow":     {"en": "AI Investment Banking · Both sides of every deal",
                         "et": "AI investeerimispangandus · Mõlemad pooled igast tehingust",
                         "lt": "AI investicinė bankininkystė · Abi sandorio pusės",
                         "lv": "AI investīciju banka · Abas darījuma puses"},
    "hero_headline_1":  {"en": "Your AI ",        "et": "Sinu AI ",         "lt": "Tavo AI ",        "lv": "Tavs AI "},
    "hero_headline_2":  {"en": "ECM / IB ",        "et": "ECM / IB ",        "lt": "ECM / IB ",       "lv": "ECM / IB "},
    "hero_headline_3":  {"en": "analyst squad ",   "et": "analüütikute meeskond ", "lt": "analitikų komanda ", "lv": "analītiķu komanda "},
    "hero_headline_4":  {"en": "for M&A ",         "et": "M&A ",             "lt": "M&A ",            "lv": "M&A "},
    "hero_headline_5":  {"en": "and ",             "et": "ja ",              "lt": "ir ",             "lv": "un "},
    "hero_headline_6":  {"en": "IPO.",             "et": "IPO.",             "lt": "IPO.",            "lv": "IPO."},
    "hero_cta_buyer":   {"en": "Buyer-Led →",     "et": "Ostja →",          "lt": "Pirkėjas →",     "lv": "Pircējs →"},
    "hero_cta_seller":  {"en": "Seller-Led →",    "et": "Müüja →",          "lt": "Pardavėjas →",   "lv": "Pārdevējs →"},

    # ── Tools ──
    "tool_free":        {"en": "Free Tool",        "et": "Tasuta tööriist",   "lt": "Nemokamas įrankis", "lv": "Bezmaksas rīks"},
    "tool_comps_title": {"en": "Market Comparables", "et": "Turu võrdlused", "lt": "Rinkos palyginimas", "lv": "Tirgus salīdzinājumi"},
    "tool_comps_sub":   {"en": "See how your business compares to sector M&A benchmarks. Enter your company URL to get started.",
                         "et": "Vaata, kuidas sinu ettevõte võrdleb sektori M&A võrdlusnäitajatega. Sisesta oma ettevõtte URL.",
                         "lt": "Sužinokite, kaip jūsų verslas atrodo lyginant su sektoriaus M&A rodikliais. Įveskite įmonės URL.",
                         "lv": "Uzziniet, kā jūsu uzņēmums salīdzinās ar nozares M&A rādītājiem. Ievadiet uzņēmuma URL."},
    "tool_match_title": {"en": "Find Buyers",     "et": "Leia ostjad",      "lt": "Raskite pirkėjus", "lv": "Atrast pircējus"},
    "tool_match_sub":   {"en": "Discover potential acquirers for your business using our Baltic & European buyer database.",
                         "et": "Avasta oma ettevõttele potentsiaalseid ostjaid meie Balti ja Euroopa ostjate andmebaasist.",
                         "lt": "Atraskite potencialius pirkėjus naudodami mūsų Baltijos ir Europos pirkėjų duomenų bazę.",
                         "lv": "Atklājiet potenciālos pircējus, izmantojot mūsu Baltijas un Eiropas pircēju datubāzi."},
    "tool_val_title":   {"en": "Business Valuation", "et": "Ettevõtte hindamine", "lt": "Verslo vertinimas", "lv": "Uzņēmuma vērtējums"},
    "tool_val_sub":     {"en": "Get an indicative valuation range based on sector benchmarks and your financials.",
                         "et": "Saa indikatiivne hinnavahemik sektori võrdlusnäitajate ja sinu finantside põhjal.",
                         "lt": "Gaukite orientacinį vertinimo diapazoną pagal sektoriaus rodiklius ir jūsų finansus.",
                         "lv": "Iegūstiet indikatīvu vērtējuma diapazonu, pamatojoties uz nozares rādītājiem un jūsu finansēm."},

    # ── Tool forms ──
    "tool_url_label":   {"en": "Enter your company website", "et": "Sisesta oma ettevõtte veebileht", "lt": "Įveskite savo įmonės svetainę", "lv": "Ievadiet sava uzņēmuma vietni"},
    "tool_url_placeholder": {"en": "e.g. https://meliva.ee", "et": "nt. https://meliva.ee", "lt": "pvz. https://meliva.ee", "lv": "piem. https://meliva.ee"},
    "tool_no_signup":   {"en": "No email or sign-up necessary. 100% confidential.",
                         "et": "E-posti ega registreerimist pole vaja. 100% konfidentsiaalne.",
                         "lt": "Nereikia el. pašto ar registracijos. 100% konfidencialu.",
                         "lv": "Nav nepieciešams e-pasts vai reģistrācija. 100% konfidenciāli."},
    "tool_next":        {"en": "Next →",           "et": "Järgmine →",       "lt": "Toliau →",       "lv": "Tālāk →"},
    "tool_financial_info": {"en": "Financial Information", "et": "Finantsteave", "lt": "Finansinė informacija", "lv": "Finanšu informācija"},
    "tool_revenue":     {"en": "Annual Revenue (EUR)", "et": "Aastakäive (EUR)", "lt": "Metinės pajamos (EUR)", "lv": "Gada ieņēmumi (EUR)"},
    "tool_profit":      {"en": "Pre-Tax Profit (EUR)", "et": "Maksueelne kasum (EUR)", "lt": "Pelnas prieš mokesčius (EUR)", "lv": "Peļņa pirms nodokļiem (EUR)"},
    "tool_salary":      {"en": "Owner Salary (EUR)", "et": "Omaniku palk (EUR)", "lt": "Savininko atlyginimas (EUR)", "lv": "Īpašnieka alga (EUR)"},
    "tool_get_comps":   {"en": "Get Market Comps →", "et": "Saa turu võrdlused →", "lt": "Gauti rinkos duomenis →", "lv": "Iegūt tirgus datus →"},
    "tool_get_val":     {"en": "Get Valuation →",   "et": "Saa hindamine →",  "lt": "Gauti vertinimą →", "lv": "Iegūt vērtējumu →"},
    "tool_find_buyers": {"en": "Find Buyers →",     "et": "Leia ostjad →",    "lt": "Rasti pirkėjus →", "lv": "Atrast pircējus →"},

    # ── Tool results ──
    "result_sector_snapshot": {"en": "Sector M&A Snapshot", "et": "Sektori M&A ülevaade", "lt": "Sektoriaus M&A apžvalga", "lv": "Nozares M&A pārskats"},
    "result_ev_revenue":  {"en": "EV / Revenue multiple", "et": "EV / Käibe kordaja", "lt": "EV / Pajamų kartotinis", "lv": "EV / Ieņēmumu reizinātājs"},
    "result_ev_ebitda":   {"en": "EV / EBITDA multiple", "et": "EV / EBITDA kordaja", "lt": "EV / EBITDA kartotinis", "lv": "EV / EBITDA reizinātājs"},
    "result_your_metrics": {"en": "Your Company Metrics", "et": "Sinu ettevõtte näitajad", "lt": "Jūsų įmonės rodikliai", "lv": "Jūsu uzņēmuma rādītāji"},
    "result_annual_rev":  {"en": "Annual Revenue",  "et": "Aastakäive",       "lt": "Metinės pajamos", "lv": "Gada ieņēmumi"},
    "result_pretax":      {"en": "Pre-Tax Profit",  "et": "Maksueelne kasum", "lt": "Pelnas prieš mokesčius", "lv": "Peļņa pirms nodokļiem"},
    "result_sde":         {"en": "Owner Salary / SDE", "et": "Omaniku palk / SDE", "lt": "Savininko atlyginimas / SDE", "lv": "Īpašnieka alga / SDE"},
    "result_val_range":   {"en": "Estimated Valuation Range", "et": "Hinnanguline hinnavahemik", "lt": "Orientacinis vertinimo diapazonas", "lv": "Indikatīvs vērtējuma diapazons"},
    "result_revenue_based": {"en": "Revenue-based (EV/Revenue)", "et": "Käibepõhine (EV/Käive)", "lt": "Pajamomis pagrįstas (EV/Pajamos)", "lv": "Ieņēmumos balstīts (EV/Ieņēmumi)"},
    "result_earnings_based": {"en": "Earnings-based (EV/EBITDA)", "et": "Kasumipõhine (EV/EBITDA)", "lt": "Pelnu pagrįstas (EV/EBITDA)", "lv": "Peļņā balstīts (EV/EBITDA)"},
    "result_estimated_range": {"en": "Estimated Range", "et": "Hinnanguline vahemik", "lt": "Orientacinis diapazonas", "lv": "Indikatīvs diapazons"},
    "result_matched_buyers": {"en": "Matched Buyers", "et": "Sobivad ostjad", "lt": "Rasti pirkėjai", "lv": "Atrasti pircēji"},
    "result_sign_up_see_all": {"en": "Sign up to see all matched buyers", "et": "Registreeru kõigi ostjate nägemiseks", "lt": "Registruokitės, kad matytumėte visus pirkėjus", "lv": "Reģistrējieties, lai redzētu visus pircējus"},

    # ── Lead capture ──
    "lead_book_call":   {"en": "Book a 15-minute call", "et": "Broneeri 15-minutiline kõne", "lt": "Užsisakykite 15 min. pokalbį", "lv": "Rezervējiet 15 minūšu zvanu"},
    "lead_speak":       {"en": "Speak with an M&A advisor about your company's potential.",
                         "et": "Räägi M&A nõustajaga oma ettevõtte potentsiaalist.",
                         "lt": "Pasitarkite su M&A konsultantu apie savo įmonės potencialą.",
                         "lv": "Aprunājieties ar M&A konsultantu par sava uzņēmuma potenciālu."},
    "lead_name":        {"en": "Full Name",        "et": "Täisnimi",          "lt": "Vardas, pavardė", "lv": "Vārds, uzvārds"},
    "lead_email":       {"en": "Email",            "et": "E-post",            "lt": "El. paštas",     "lv": "E-pasts"},
    "lead_phone":       {"en": "Phone (optional)", "et": "Telefon (valikuline)", "lt": "Telefonas (neprivaloma)", "lv": "Tālrunis (neobligāti)"},
    "lead_timeline":    {"en": "Timeline",         "et": "Ajakava",           "lt": "Terminai",       "lv": "Laika grafiks"},
    "lead_immediately": {"en": "Immediately",      "et": "Kohe",              "lt": "Nedelsiant",     "lv": "Nekavējoties"},
    "lead_1_3_months":  {"en": "1-3 months",       "et": "1-3 kuud",          "lt": "1-3 mėnesiai",   "lv": "1-3 mēneši"},
    "lead_3_6_months":  {"en": "3-6 months",       "et": "3-6 kuud",          "lt": "3-6 mėnesiai",   "lv": "3-6 mēneši"},
    "lead_6_12_months": {"en": "6-12 months",      "et": "6-12 kuud",         "lt": "6-12 mėnesių",   "lv": "6-12 mēneši"},
    "lead_exploring":   {"en": "Just exploring",   "et": "Lihtsalt uurin",    "lt": "Tik žvalgausi",  "lv": "Tikai izpētu"},
    "lead_book_btn":    {"en": "Book Call →",      "et": "Broneeri kõne →",   "lt": "Rezervuoti →",   "lv": "Rezervēt zvanu →"},
    "lead_thank_you":   {"en": "Thank you! We'll be in touch shortly.",
                         "et": "Aitäh! Võtame teiega peagi ühendust.",
                         "lt": "Ačiū! Netrukus su jumis susisieksime.",
                         "lv": "Paldies! Mēs drīz sazināsimies."},

    # ── Industries ──
    "ind_title":        {"en": "Industries We Serve", "et": "Tööstused, mida teenindame", "lt": "Pramonės šakos, kurias aptarnaujame", "lv": "Nozares, ko apkalpojam"},
    "ind_subtitle":     {"en": "Sector-specific M&A advisory across the Baltics and Nordics.",
                         "et": "Sektoripõhine M&A nõustamine Baltikumis ja Põhjamaades.",
                         "lt": "Sektoriui specifinės M&A konsultacijos Baltijos ir Šiaurės šalyse.",
                         "lv": "Nozarei specifiskas M&A konsultācijas Baltijā un Ziemeļvalstīs."},
    "ind_sub_sectors":  {"en": "Sub-Sectors We Cover", "et": "Allsektorid", "lt": "Subsektoriai", "lv": "Apakšnozares"},
    "ind_advisor_title": {"en": "Work With a Local Advisor", "et": "Tööta kohaliku nõustajaga", "lt": "Dirbkite su vietiniu konsultantu", "lv": "Strādājiet ar vietējo konsultantu"},
    "ind_curious":      {"en": "Curious About Your Potential Buyers?",
                         "et": "Huvitatud oma potentsiaalsetest ostjatest?",
                         "lt": "Domina potencialūs pirkėjai?",
                         "lv": "Interesē potenciālie pircēji?"},
    "ind_curious_sub":  {"en": "Enter your company website to see matched buyers.",
                         "et": "Sisesta oma ettevõtte veebileht sobivate ostjate nägemiseks.",
                         "lt": "Įveskite svetainę, kad matytumėte tinkamus pirkėjus.",
                         "lv": "Ievadiet vietni, lai redzētu piemērotus pircējus."},
    "ind_faq_title":    {"en": "Frequently Asked Questions", "et": "Korduma kippuvad küsimused", "lt": "Dažnai užduodami klausimai", "lv": "Bieži uzdotie jautājumi"},

    # ── Valuation results ──
    "val_step1":        {"en": "Step 1: Deal Comparables", "et": "1. samm: Tehingute võrdlused", "lt": "1 žingsnis: Sandorių palyginimai", "lv": "1. solis: Darījumu salīdzinājumi"},
    "val_step2":        {"en": "Step 2: Value Drivers",    "et": "2. samm: Väärtuse tegurid",    "lt": "2 žingsnis: Vertės veiksniai",    "lv": "2. solis: Vērtības faktori"},
    "val_step3":        {"en": "Step 3: Valuation Range",  "et": "3. samm: Hinnavahemik",        "lt": "3 žingsnis: Vertinimo diapazonas", "lv": "3. solis: Vērtējuma diapazons"},
    "val_enterprise":   {"en": "Estimated Enterprise Value", "et": "Hinnanguline ettevõtte väärtus", "lt": "Orientacinė įmonės vertė", "lv": "Indikatīvā uzņēmuma vērtība"},
    "val_midpoint":     {"en": "Midpoint",          "et": "Keskpunkt",         "lt": "Vidurkis",        "lv": "Viduspunkts"},
    "val_disclaimer":   {"en": "This is an indicative range based on sector benchmarks. A formal valuation requires detailed financial analysis.",
                         "et": "See on indikatiivne vahemik sektori võrdlusnäitajate alusel. Formaalne hindamine nõuab üksikasjalikku finantsanalüüsi.",
                         "lt": "Tai orientacinis diapazonas pagal sektoriaus rodiklius. Formaliam vertinimui reikia detalios finansinės analizės.",
                         "lv": "Šis ir indikatīvs diapazons, balstoties uz nozares rādītājiem. Formālam vērtējumam nepieciešama detalizēta finanšu analīze."},

    # ── Footer ──
    "footer_contact":   {"en": "Contact",           "et": "Kontakt",           "lt": "Kontaktai",      "lv": "Kontakti"},

    # ── Common ──
    "get_started":      {"en": "Get Started →",     "et": "Alusta →",          "lt": "Pradėti →",      "lv": "Sākt →"},
    "get_in_touch":     {"en": "Get in touch →",    "et": "Võta ühendust →",   "lt": "Susisiekite →",  "lv": "Sazināties →"},
    "sector":           {"en": "Sector",             "et": "Sektor",            "lt": "Sektorius",      "lv": "Nozare"},
    "sub_sector":       {"en": "Sub-sector",         "et": "Allsektor",         "lt": "Subsektorius",   "lv": "Apakšnozare"},
    "products_services": {"en": "Products & Services", "et": "Tooted ja teenused", "lt": "Produktai ir paslaugos", "lv": "Produkti un pakalpojumi"},
    "end_markets":      {"en": "End Markets",        "et": "Lõppturud",         "lt": "Galutinės rinkos", "lv": "Gala tirgi"},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Look up a translation. Falls back to English, then to the key itself."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("en", key))


def get_lang(sess: dict[str, Any], request=None) -> str:
    """Get language from session."""
    lang = (sess.get("lang") or "").lower()
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def set_lang(sess: dict[str, Any], lang: str) -> str:
    """Set language in session, return the resolved code."""
    code = (lang or "").lower()
    if code in SUPPORTED_LANGS:
        sess["lang"] = code
    return get_lang(sess)
