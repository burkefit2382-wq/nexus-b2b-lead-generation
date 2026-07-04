import os


SAMPLE_PACK = {
    "title": "NEXUS Sample Pilot Pack - Tampa Bay Cleaning Services",
    "region": "Pinellas / Hillsborough / Pasco County, FL",
    "note": ("Representative SAMPLE of the quality delivered in a live 5-lead pilot. Every lead is "
             "OSINT-verified and AI-scored 92+, exclusive to the buyer. Contact details are masked and "
             "unlock on purchase. Figures are illustrative and editable to your exact market."),
    "pricing": "5 leads = $200 ($40/lead)  |  10 leads = $350 ($35/lead)",
    "leads": [
        {"rank": 1, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Pinellas", "city": "Palm Harbor, FL",
         "entity_masked": "Waterfront Residence - Palm Harbor",
         "contact_masked": "•••@•••  ·  (727) •••-••17", "score": 96, "tier": "Strategic",
         "budget_est": "$190-$260 / mo (recurring)",
         "intent_summary": "4BR/3BA waterfront home; owner seeking reliable bi-weekly whole-home cleaning after a recent move-in. High-intent, recurring, insured-preferred.",
         "verification_nodes": ["Address verified", "Phone valid", "Property records matched", "Intent confirmed", "Geo-located"],
         "source": "OSINT · public listing + permit + review signals"},
        {"rank": 2, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Pasco", "city": "Wesley Chapel, FL",
         "entity_masked": "New-Build Household - Wesley Chapel",
         "contact_masked": "•••@•••  ·  (813) •••-••04", "score": 94, "tier": "Strategic",
         "budget_est": "$220-$300 one-time + $150/mo",
         "intent_summary": "New-construction move-in; homeowner requesting a deep move-in clean then monthly maintenance. Dual-income, time-poor, ready to book.",
         "verification_nodes": ["Address verified", "Email valid", "Property records matched", "Intent confirmed"],
         "source": "OSINT · new-home permit + local group signals"},
        {"rank": 3, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Hillsborough", "city": "Tampa (Hyde Park), FL",
         "entity_masked": "Historic Home - South Tampa",
         "contact_masked": "•••@•••  ·  (813) •••-••88", "score": 93, "tier": "Tactical",
         "budget_est": "$160-$220 / mo (weekly)",
         "intent_summary": "Dual-income professional household in Hyde Park seeking weekly maid service; values eco-friendly products and vetted, background-checked staff.",
         "verification_nodes": ["Address verified", "Phone valid", "Footprint consistent", "Geo-located"],
         "source": "OSINT · public listing + review + social signals"},
        {"rank": 4, "type": "Commercial", "category": "commercial_cleaning",
         "county": "Pinellas", "city": "Clearwater, FL",
         "entity_masked": "Dental / Medical Practice - Clearwater",
         "contact_masked": "office•••@•••  ·  (727) •••-••31", "score": 95, "tier": "Strategic",
         "budget_est": "$1,400-$2,100 / mo (nightly janitorial)",
         "intent_summary": "~6,000 sqft dental/medical office needs nightly janitorial with medical-grade sanitation and restroom service. Decision-maker is the practice manager; renewing off a lapsed vendor.",
         "verification_nodes": ["Business registry verified", "Phone valid", "Address verified", "Intent confirmed", "Geo-located"],
         "source": "OSINT · registry + license + review signals"},
        {"rank": 5, "type": "Commercial", "category": "commercial_cleaning",
         "county": "Hillsborough", "city": "Brandon, FL",
         "entity_masked": "Multi-Tenant Office Park - Brandon",
         "contact_masked": "pm•••@•••  ·  (813) •••-••62", "score": 92, "tier": "Tactical",
         "budget_est": "$2,600-$3,800 / mo (common areas + restrooms)",
         "intent_summary": "Property manager sourcing common-area, lobby and restroom cleaning across a multi-tenant office park; wants one accountable vendor and a fixed monthly scope.",
         "verification_nodes": ["Business registry verified", "Email valid", "Address verified", "Footprint consistent"],
         "source": "OSINT · registry + property mgmt + review signals"},
    ],
}

def _sample_pack_csv() -> str:
    import io, csv
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Rank", "Type", "Category", "County", "City", "Entity (masked)", "Contact (masked)",
                "Score", "Tier", "Budget Est", "Intent Summary", "Verification Nodes", "Source"])
    for l in SAMPLE_PACK["leads"]:
        w.writerow([l["rank"], l["type"], l["category"], l["county"], l["city"], l["entity_masked"],
                    l["contact_masked"], l["score"], l["tier"], l["budget_est"], l["intent_summary"],
                    " | ".join(l["verification_nodes"]), l["source"]])
    return out.getvalue()

def _pdf_txt(s: str) -> str:
    s = str(s)
    for k, v in {"•": "*", "–": "-", "—": "-", "·": "-", "’": "'", "“": '"', "”": '"', "…": "..."}.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

def _sample_pack_pdf() -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    import io, qrcode
    LIME = (159, 232, 112); DARK = (13, 26, 18); GREEN = (34, 110, 58)
    GREY = (95, 95, 95); INK = (25, 25, 25)
    p = FPDF(format="A4")
    p.set_auto_page_break(False)

    # ---------- Cover ----------
    p.add_page()
    p.set_fill_color(*DARK); p.rect(0, 0, 210, 62, "F")
    p.set_xy(15, 13); p.set_text_color(*LIME); p.set_font("Helvetica", "B", 12)
    p.cell(0, 6, _pdf_txt("NEXUS LEAD INTELLIGENCE"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(15); p.set_text_color(255, 255, 255); p.set_font("Helvetica", "B", 26)
    p.cell(0, 13, _pdf_txt("Sample Pilot Pack"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(15); p.set_text_color(205, 225, 210); p.set_font("Helvetica", "", 13)
    p.cell(0, 7, _pdf_txt("5 AI-scored cleaning leads (92+) - Tampa Bay"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(15); p.set_text_color(150, 180, 155); p.set_font("Helvetica", "", 10)
    p.cell(0, 6, _pdf_txt(SAMPLE_PACK["region"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    p.set_y(72); p.set_text_color(*INK); p.set_font("Helvetica", "", 11)
    p.multi_cell(0, 5.5, _pdf_txt("A representative sample of what a live NEXUS pilot delivers: verified, exclusive, "
        "ready-to-work cleaning opportunities across Pinellas, Hillsborough and Pasco counties - each researched "
        "from public sources, AI-scored, and enriched so your team knows exactly why the lead matters and what to "
        "say first."))
    p.ln(4)
    p.set_font("Helvetica", "B", 12); p.set_text_color(*GREEN)
    p.cell(0, 7, _pdf_txt("What's inside"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_font("Helvetica", "", 10.5); p.set_text_color(*INK)
    for b in ["5 high-quality leads - 3 residential home-cleaning + 2 commercial cleaning",
              "Every lead OSINT-verified and AI-scored 92+ (out of 100)",
              "Exclusive to you - never resold or shared",
              "Budget estimate, intent summary and verification nodes on each",
              "Delivered as a clean PDF + CSV your crew can act on today"]:
        p.set_x(17); p.multi_cell(0, 5.5, _pdf_txt("- " + b))
    p.ln(4)
    y = p.get_y(); p.set_fill_color(240, 248, 240); p.set_draw_color(*GREEN)
    p.rect(15, y, 180, 22, "DF")
    p.set_xy(20, y + 4); p.set_text_color(*GREEN); p.set_font("Helvetica", "B", 12)
    p.cell(0, 6, _pdf_txt("Pilot pricing"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(20); p.set_text_color(*INK); p.set_font("Helvetica", "B", 11)
    p.cell(0, 6, _pdf_txt("5 leads = $200 ($40/lead)        |        10 leads = $350 ($35/lead)"),
           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_y(y + 27); p.set_text_color(*GREY); p.set_font("Helvetica", "I", 8.5)
    p.multi_cell(0, 4, _pdf_txt("Representative sample - names and contact details are masked and unlock on purchase. "
                                "Figures are editable. Prepared by NEXUS Lead Intelligence - nexuscloud.sh"))

    # ---------- Booking CTA + QR code ----------
    site = os.environ.get("PUBLIC_SITE_URL", "https://nexuscloud.sh")
    site_label = site.replace("https://", "").replace("http://", "").rstrip("/")
    cy = p.get_y() + 8
    if cy > 233:
        cy = 233
    p.set_fill_color(*DARK); p.rect(15, cy, 180, 52, "F")
    p.set_fill_color(*LIME); p.rect(15, cy, 3, 52, "F")
    p.set_xy(24, cy + 9); p.set_text_color(*LIME); p.set_font("Helvetica", "B", 9)
    p.cell(0, 5, _pdf_txt("READY TO ACTIVATE YOUR PIPELINE?"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(24); p.set_text_color(255, 255, 255); p.set_font("Helvetica", "B", 22)
    p.cell(0, 12, _pdf_txt("Schedule a demo"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(24); p.set_text_color(205, 225, 210); p.set_font("Helvetica", "", 10)
    p.cell(0, 5.5, _pdf_txt("Scan the code or visit"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(24); p.set_text_color(*LIME); p.set_font("Helvetica", "B", 13)
    p.cell(0, 6, _pdf_txt(site_label), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_fill_color(255, 255, 255); p.rect(150, cy + 6, 40, 40, "F")
    qbuf = io.BytesIO(); qrcode.make(site).save(qbuf, format="PNG"); qbuf.seek(0)
    p.image(qbuf, x=153, y=cy + 9, w=34, h=34)
    p.link(15, cy, 180, 52, site)

    # ---------- One page per lead ----------
    def _section(title, body, is_list=False):
        p.set_text_color(*GREEN); p.set_font("Helvetica", "B", 11)
        p.cell(0, 6, _pdf_txt(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        p.set_text_color(*INK); p.set_font("Helvetica", "", 10.5)
        if is_list:
            for x in body:
                p.set_x(17); p.multi_cell(0, 5.2, _pdf_txt("+  " + x))
        else:
            p.multi_cell(0, 5.5, _pdf_txt(body))
        p.ln(3)

    total = len(SAMPLE_PACK["leads"])
    for l in SAMPLE_PACK["leads"]:
        p.add_page()
        p.set_fill_color(*DARK); p.rect(0, 0, 210, 30, "F")
        p.set_text_color(*LIME); p.set_font("Helvetica", "B", 15)
        p.set_xy(15, 10); p.cell(120, 8, _pdf_txt(f"LEAD #{l['rank']}  -  {l['type'].upper()} CLEANING"))
        p.set_text_color(255, 255, 255); p.set_font("Helvetica", "B", 20)
        p.set_xy(140, 7); p.cell(55, 9, _pdf_txt(f"{l['score']}/100"), align="R")
        p.set_text_color(*LIME); p.set_font("Helvetica", "B", 9)
        p.set_xy(140, 18); p.cell(55, 5, _pdf_txt(l["tier"].upper() + " TIER"), align="R")

        p.set_y(40); p.set_text_color(*GREEN); p.set_font("Helvetica", "B", 15)
        p.multi_cell(0, 7, _pdf_txt(l["entity_masked"]))
        p.set_text_color(*GREY); p.set_font("Helvetica", "", 11)
        p.set_x(15); p.multi_cell(0, 6, _pdf_txt(f"{l['city']}  -  {l['county']} County, FL"))
        p.ln(4)
        _section("The opportunity", l["intent_summary"])
        _section("Estimated budget", l["budget_est"])
        _section("Verification nodes", l["verification_nodes"], is_list=True)
        _section("Contact", l["contact_masked"] + "   (unlocks on purchase)")
        p.set_text_color(*GREY); p.set_font("Helvetica", "I", 8.5)
        p.multi_cell(0, 4, _pdf_txt("Source: " + l["source"]))
        p.set_y(-15); p.set_text_color(*GREY); p.set_font("Helvetica", "", 8)
        p.cell(0, 6, _pdf_txt(f"NEXUS Lead Intelligence  -  nexuscloud.sh          Lead {l['rank']} of {total}"), align="C")

    return bytes(p.output())

def _sample_pack_attachment() -> list:
    pdf = _sample_pack_pdf()
    return [{"filename": "NEXUS_Sample_Pilot_Pack.pdf",
             "content": list(pdf),
             "content_type": "application/pdf"}]
