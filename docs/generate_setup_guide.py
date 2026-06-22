"""
Generate the Arad Quality Intelligence — Setup & User Guide (PDF).

A branded, quality-engineer-friendly hand-off document covering the full journey:
install -> first sign-in -> connect tools (API keys) -> bring in data -> test.

Run:  .venv\\Scripts\\python.exe docs\\generate_setup_guide.py
Output: docs/Arad_Quality_Setup_Guide.pdf
"""

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, NextPageTemplate,
)

# ---------------------------------------------------------------- brand palette
NAVY      = HexColor("#0B1B2E")
NAVY_SOFT = HexColor("#12263D")
ACCENT    = HexColor("#4E8CFF")
ACCENT_DK = HexColor("#2F6BE0")
ACCENT_LT = HexColor("#9DBFFF")
INK       = HexColor("#1A2433")
BODY      = HexColor("#33414F")
MUTED     = HexColor("#64748B")
HAIR      = HexColor("#D8E0EA")
PANEL     = HexColor("#F4F7FB")
ZEBRA     = HexColor("#F8FAFD")

INFO_BG, INFO_BAR   = HexColor("#EAF1FF"), ACCENT
TIP_BG,  TIP_BAR    = HexColor("#E9F7EF"), HexColor("#16A34A")
WARN_BG, WARN_BAR   = HexColor("#FEF4E6"), HexColor("#D97706")

PAGE_W, PAGE_H = A4
LMARGIN = RMARGIN = 16 * mm
TMARGIN = 18 * mm
BMARGIN = 16 * mm
CONTENT_W = PAGE_W - LMARGIN - RMARGIN

DATE_STR = "June 2026"
VERSION  = "Version 1.0"

# ---------------------------------------------------------------- styles
ss = getSampleStyleSheet()


def style(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


S_H1 = style("H1", fontName="Helvetica-Bold", fontSize=16, leading=20,
             textColor=NAVY, spaceBefore=4, spaceAfter=2, keepWithNext=True)
S_KICKER = style("Kicker", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                 textColor=ACCENT_DK, spaceAfter=2, tracking=1)
S_H2 = style("H2", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
             textColor=INK, spaceBefore=10, spaceAfter=3, keepWithNext=True)
S_BODY = style("Body", fontName="Helvetica", fontSize=9.7, leading=14.5,
               textColor=BODY, alignment=TA_LEFT, spaceAfter=5)
S_LEAD = style("Lead", parent=S_BODY, fontSize=10.3, leading=15.5, textColor=INK)
S_BULLET = style("Bullet", parent=S_BODY, leftIndent=14, bulletIndent=2, spaceAfter=3)
S_STEP = style("Step", parent=S_BODY, leftIndent=20, spaceAfter=5)
S_CELL = style("Cell", fontName="Helvetica", fontSize=8.8, leading=12, textColor=BODY)
S_CELL_B = style("CellB", parent=S_CELL, fontName="Helvetica-Bold", textColor=INK)
S_CELL_H = style("CellH", parent=S_CELL, fontName="Helvetica-Bold", textColor=white, fontSize=8.8)
S_CALL = style("Call", fontName="Helvetica", fontSize=9.3, leading=13.5, textColor=INK)
S_MONO = style("Mono", fontName="Courier-Bold", fontSize=9, leading=13, textColor=NAVY)
S_TOC = style("Toc", parent=S_BODY, fontSize=10, leading=17, spaceAfter=0)


# ---------------------------------------------------------------- helpers
def para(txt, st=S_BODY):
    return Paragraph(txt, st)


def bullet(txt):
    return Paragraph(f"<font color='#4E8CFF'>•</font>&nbsp;&nbsp;{txt}", S_BULLET)


def step(n, txt):
    return Paragraph(
        f"<font name='Helvetica-Bold' color='#2F6BE0'>{n}.</font>&nbsp;&nbsp;{txt}",
        S_STEP,
    )


def code(txt):
    """Inline-looking command on its own shaded line."""
    t = Table([[Paragraph(txt, S_MONO)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EEF2F8")),
        ("BOX", (0, 0), (-1, -1), 0.5, HAIR),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def callout(kind, html):
    bg, bar, label = {
        "info": (INFO_BG, INFO_BAR, "NOTE"),
        "tip":  (TIP_BG, TIP_BAR, "TIP"),
        "warn": (WARN_BG, WARN_BAR, "IMPORTANT"),
    }[kind]
    inner = Paragraph(
        f"<font name='Helvetica-Bold' color='#{bar.hexval()[2:]}'>{label}&nbsp;&nbsp;</font>{html}",
        S_CALL,
    )
    t = Table([["", inner]], colWidths=[4, CONTENT_W - 4])
    t.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), bg),
        ("BACKGROUND", (0, 0), (0, 0), bar),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (1, 0), (1, 0), 8),
        ("BOTTOMPADDING", (1, 0), (1, 0), 8),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return KeepTogether([Spacer(1, 2), t, Spacer(1, 6)])


def table(rows, widths, header=True):
    """rows: list of lists of strings (rendered as wrapped cell paragraphs)."""
    data = []
    for r, row in enumerate(rows):
        cells = []
        for c, val in enumerate(row):
            if header and r == 0:
                cells.append(Paragraph(val, S_CELL_H))
            elif c == 0:
                cells.append(Paragraph(val, S_CELL_B))
            else:
                cells.append(Paragraph(val, S_CELL))
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    sty = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HAIR),
        ("BOX", (0, 0), (-1, -1), 0.5, HAIR),
    ]
    if header:
        sty += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]
        for r in range(2, len(rows), 2):
            sty.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    return KeepTogether([Spacer(1, 2), t, Spacer(1, 6)])


def h1(num, title):
    bar = Table([[""]], colWidths=[26], rowHeights=[3])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    return KeepTogether([
        Spacer(1, 6), bar, Spacer(1, 3),
        Paragraph(f"{num}&nbsp;&nbsp;&nbsp;{title}", S_H1),
        Spacer(1, 4),
    ])


# ---------------------------------------------------------------- cover + footer
def draw_cover(canvas, doc):
    canvas.saveState()
    # navy band
    band_h = 360
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - band_h, PAGE_W, band_h, fill=1, stroke=0)
    canvas.setFillColor(NAVY_SOFT)
    canvas.rect(0, PAGE_H - band_h, PAGE_W, 1, fill=1, stroke=0)
    # accent underline of band
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - band_h - 4, PAGE_W, 4, fill=1, stroke=0)

    x = LMARGIN
    # brand mark
    mark = 50
    my = PAGE_H - 96
    canvas.setFillColor(ACCENT)
    canvas.roundRect(x, my, mark, mark, 12, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawCentredString(x + mark / 2, my + mark / 2 - 8, "AQ")

    canvas.setFillColor(ACCENT_LT)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(x + mark + 14, my + 30, "Q U A L I T Y   I N T E L L I G E N C E")

    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 31)
    canvas.drawString(x, PAGE_H - 188, "Arad Quality Intelligence")
    canvas.setFillColor(ACCENT_LT)
    canvas.setFont("Helvetica", 18)
    canvas.drawString(x, PAGE_H - 216, "Setup & User Guide")

    canvas.setFillColor(HexColor("#C7D6EC"))
    canvas.setFont("Helvetica", 11.5)
    canvas.drawString(x, PAGE_H - 250, "Install, configure, and run your platform — from start to finish.")
    canvas.setFont("Helvetica-Oblique", 10)
    canvas.drawString(x, PAGE_H - 270, "Written for quality engineers. No coding required.")

    # meta panel
    py = PAGE_H - band_h - 4 - 110
    canvas.setFillColor(PANEL)
    canvas.roundRect(x, py, CONTENT_W, 92, 8, fill=1, stroke=0)
    canvas.setStrokeColor(HAIR)
    canvas.setLineWidth(0.6)
    canvas.roundRect(x, py, CONTENT_W, 92, 8, fill=0, stroke=1)

    rows = [
        ("Version", f"{VERSION}  ·  {DATE_STR}"),
        ("Audience", "Quality Engineers  &  IT / whoever installs it"),
        ("Covers", "Install  →  Setup  →  Connect tools  →  Data  →  Testing"),
    ]
    ry = py + 70
    for label, val in rows:
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(x + 16, ry, label.upper())
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica", 10.5)
        canvas.drawString(x + 96, ry, val)
        ry -= 24

    # footer line on cover
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(x, 40, "Keep this guide with your project files — hand it to whoever operates the system.")
    canvas.setFillColor(ACCENT_DK)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawRightString(PAGE_W - RMARGIN, 40, "Arad Group")
    canvas.restoreState()


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(HAIR)
    canvas.setLineWidth(0.6)
    canvas.line(LMARGIN, BMARGIN - 6, PAGE_W - RMARGIN, BMARGIN - 6)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(LMARGIN, BMARGIN - 16, "Arad Quality Intelligence — Setup & User Guide")
    canvas.setFillColor(ACCENT_DK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(PAGE_W - RMARGIN, BMARGIN - 16, f"Page {doc.page - 1}")
    canvas.restoreState()


# ---------------------------------------------------------------- build story
def build():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "Arad_Quality_Setup_Guide.pdf")

    doc = BaseDocTemplate(
        out, pagesize=A4,
        leftMargin=LMARGIN, rightMargin=RMARGIN, topMargin=TMARGIN, bottomMargin=BMARGIN,
        title="Arad Quality Intelligence — Setup & User Guide",
        author="Arad Group", subject="Installation, setup and user guide",
    )
    frame = Frame(LMARGIN, BMARGIN, CONTENT_W, PAGE_H - TMARGIN - BMARGIN, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=draw_cover),
        PageTemplate(id="body", frames=[frame], onPage=draw_footer),
    ])

    s = []
    # page 1 is the drawn cover; switch to the body template and push content to page 2
    s.append(NextPageTemplate("body"))
    s.append(PageBreak())

    # ---- Contents ----
    s.append(Paragraph("What's inside", S_H1))
    s.append(Spacer(1, 4))
    toc = [
        "1   What is Arad Quality?",
        "2   Before you start — what you'll need",
        "3   Part 1 · Install the app  (one-time, technical)",
        "4   Part 2 · First sign-in & the welcome tour",
        "5   Part 3 · Connect your tools  (fill in API keys)",
        "6   Part 4 · Get your data in",
        "7   Part 5 · Set up your quality workspace",
        "8   Part 6 · Test that everything works",
        "9   Troubleshooting",
        "10  Glossary",
        "11  Quick reference",
    ]
    for line in toc:
        s.append(Paragraph(line, S_TOC))
    s.append(callout("tip",
        "New here? Read in order. If the platform is already installed and you can open it "
        "in a browser, jump to <b>Part 2</b>."))

    # ---- 1. What is Arad Quality ----
    s.append(h1("1", "What is Arad Quality?"))
    s.append(para(
        "Arad Quality Intelligence is an <b>autonomous quality-control platform</b>. It continuously "
        "watches your measurement data, runs Statistical Process Control (SPC) and Gage R&amp;R (GR&amp;R) "
        "analysis, raises an alert the moment a process drifts out of control, and explains what's "
        "happening in plain language with an AI copilot. You drive everything from one web dashboard.",
        S_LEAD))
    s.append(Paragraph("Who does what", S_H2))
    s.append(table([
        ["Role", "What they do", "How often"],
        ["The person who installs it<br/>(you or IT)", "Puts the platform on a server or PC, sets a few security passwords, and starts it.", "Once, at the start"],
        ["You — the quality engineer", "Sign in, connect your alert tools, bring in your data, set up gages and processes, run studies.", "Day to day, in the browser"],
    ], [CONTENT_W*0.30, CONTENT_W*0.46, CONTENT_W*0.24]))
    s.append(callout("tip",
        "You do <b>not</b> need to be a programmer. Once it's installed, everything in this guide is "
        "done by clicking around the dashboard."))

    # ---- 2. Before you start ----
    s.append(h1("2", "Before you start — what you'll need"))
    s.append(para("Gather these before the first-time setup. Most are optional and can be added later.", S_LEAD))
    s.append(bullet("A computer or server to run it on, with <b>Docker Desktop</b> installed — this is the only technical prerequisite."))
    s.append(bullet("About <b>30 minutes</b> for the one-time install."))
    s.append(bullet("Your measurement data as a <b>CSV or Excel file</b> (or your machine / MES system's API details if IT will connect it directly)."))
    s.append(bullet("<i>Optional</i> — sign-in details for any tools you want alerts sent to: a <b>Slack</b> webhook link, your <b>email</b> (SMTP) details, a <b>Twilio</b> account for texts, and a free <b>Google Gemini</b> key for AI summaries."))
    s.append(callout("info",
        "Don't have the optional pieces yet? That's fine — install first, then add each tool later whenever "
        "you're ready. Nothing breaks if you skip them."))

    # ---- 3. Part 1 Install ----
    s.append(h1("3", "Part 1 · Install the app  (one-time, technical)"))
    s.append(para(
        "This part is done once by whoever sets up the server. If your platform is already running and you "
        "can open it in a browser, skip to <b>Part 2</b>.", S_LEAD))
    s.append(step(1, "Install <b>Docker Desktop</b> (Docker Engine 25+, Compose 2.20+) on the host machine. Make sure ports <b>3000, 8000, 5432</b> and <b>9092</b> are free."))
    s.append(step(2, "Copy the project folder onto the machine and open a terminal inside it."))
    s.append(step(3, "Create your settings file from the template:"))
    s.append(code("cp .env.example .env&nbsp;&nbsp;&nbsp;# Windows PowerShell: Copy-Item .env.example .env"))
    s.append(step(4, "Open <b>.env</b> and set the security values below (at minimum the first four). Tip: set <b>SEED_DEMO_DATA=true</b> for the very first run so you have sample data to explore."))
    s.append(table([
        ["Setting in .env", "What to put", "Why it matters"],
        ["API_AUTH_KEY", "A long random secret (32+ characters)", "Lets the dashboard talk to the server securely"],
        ["JWT_SECRET", "A different long random secret", "Protects user logins"],
        ["POSTGRES_PASSWORD", "A strong database password", "Protects your stored data"],
        ["ADMIN_USERNAME / ADMIN_PASSWORD", "Your first sign-in details", "Creates the first dashboard login automatically"],
        ["SEED_DEMO_DATA", "true (first run) / false", "Loads sample measurements so you can explore"],
    ], [CONTENT_W*0.32, CONTENT_W*0.36, CONTENT_W*0.32]))
    s.append(callout("tip",
        "Need a strong random secret? Run:&nbsp; "
        "<font name='Courier-Bold'>python -c \"import secrets; print(secrets.token_urlsafe(48))\"</font>"))
    s.append(step(5, "Start everything with one command (the first run downloads and builds the services — a few minutes):"))
    s.append(code("docker compose up --build -d"))
    s.append(step(6, "Wait until it reports ready, then open the dashboard at <b>http://localhost:3000</b>."))
    s.append(callout("warn",
        "Keep your <b>.env</b> file private — it holds passwords. Never email it or commit it to a public place."))
    s.append(Paragraph("Useful addresses", S_H2))
    s.append(table([
        ["Address", "What it is"],
        ["http://localhost:3000", "The dashboard — where you do your work"],
        ["http://localhost:8000/health/ready", "Server health check (should say \"ready\")"],
        ["http://localhost:3002", "Grafana — optional system monitoring for IT"],
    ], [CONTENT_W*0.45, CONTENT_W*0.55]))
    s.append(para(
        "<i>Running in the background:</i> the database (TimescaleDB, 5432), the data stream (Kafka, 9092) "
        "and the cache (Redis, 6379). You don't interact with these directly.", S_BODY))

    # ---- 4. Part 2 First sign-in ----
    s.append(h1("4", "Part 2 · First sign-in & the welcome tour"))
    s.append(step(1, "Open <b>http://localhost:3000</b> and sign in with the <b>ADMIN_USERNAME / ADMIN_PASSWORD</b> you set in .env."))
    s.append(step(2, "A <b>Getting Started</b> guide pops up the first time — four short steps that show you around. You can reopen it anytime from <b>“Getting started”</b> at the bottom-left of the sidebar."))
    s.append(step(3, "Click the <b>Settings</b> gear (bottom-left). You should see a green <b>“Connected to your quality server.”</b> There's nothing to set up here — the technical address and key live under <i>“Advanced — for IT”</i> and you can ignore them."))
    s.append(callout("info",
        "If Settings says <b>“Can't reach your quality server,”</b> the backend isn't running — ask whoever "
        "installed it to check Part 1 (that Docker is up). You never fix this inside the app."))

    # ---- 5. Part 3 Connect tools ----
    s.append(h1("5", "Part 3 · Connect your tools  (fill in your API keys)"))
    s.append(para(
        "Open <b>Connections</b> from the left sidebar (under “Setup”). This is where you choose <b>where "
        "alerts go</b> and <b>how data comes in</b>. Everything you type here is encrypted on your own server "
        "and never shown again after saving. Fill in only what you use.", S_LEAD))
    s.append(Paragraph("“Where should alerts go?” — the ones you'll most likely use", S_H2))
    s.append(table([
        ["Tool", "What you enter", "Where to get it"],
        ["Slack", "Slack webhook link", "Slack → Apps → Incoming Webhooks → add to a channel"],
        ["Email", "Mail server (SMTP) host, port, username, password, send-from &amp; send-to addresses", "Your email / IT provider"],
        ["Text message", "Twilio API URL, auth token, from &amp; to numbers", "Your Twilio account"],
    ], [CONTENT_W*0.18, CONTENT_W*0.52, CONTENT_W*0.30]))
    s.append(Paragraph("“Advanced connections” — usually set up once by IT", S_H2))
    s.append(table([
        ["Tool", "What you enter", "Purpose"],
        ["JIRA", "JIRA address, account email, API token, project key", "Auto-create a ticket when a study fails or a problem repeats"],
        ["QMS", "QMS events URL", "Send quality events to your quality system"],
        ["Automatic data feed (MES)", "Measurements API URL, token, field map", "Pull measurements automatically (see Part 4)"],
        ["AI summaries (Gemini)", "Gemini API key", "Plain-English write-ups on results and alerts"],
    ], [CONTENT_W*0.26, CONTENT_W*0.40, CONTENT_W*0.34]))
    s.append(Paragraph("To connect any tool", S_H2))
    s.append(step(1, "Type the values into that tool's box."))
    s.append(step(2, "Click <b>Save changes</b> (top right)."))
    s.append(step(3, "Click <b>Send test</b> on that tool. A green <b>“Working”</b> badge means it's set up correctly. <b>“Test failed”</b> means re-check the value and try again."))
    s.append(callout("tip",
        "For a free AI key, open <b>Google AI Studio</b>, create an API key, and paste it into “AI summaries.” "
        "SPC and GR&amp;R work fine without it — you just won't get the AI narratives."))

    # ---- 6. Part 4 Data ----
    s.append(h1("6", "Part 4 · Get your data in"))
    s.append(para(
        "The platform analyses whatever measurements you give it. There are three ways to get data in — "
        "pick whichever fits.", S_LEAD))
    s.append(Paragraph("A.  Upload a spreadsheet  (easiest)", S_H2))
    s.append(para(
        "On the <b>Connections</b> page, under “Upload a spreadsheet,” click <b>Choose file</b> and pick a CSV "
        "or Excel export. Columns are detected automatically and the monitor starts analysing the new data "
        "right away. One row per measurement:", S_BODY))
    s.append(table([
        ["Column", "Example", "Required?"],
        ["timestamp", "2026-06-16 08:30", "Yes"],
        ["part_number", "PN-1042", "Yes"],
        ["measured_value", "12.503", "Yes"],
        ["characteristic_name", "Bore diameter", "Recommended"],
        ["nominal_value", "12.500", "Optional"],
        ["unit", "mm", "Optional"],
        ["equipment_id", "CNC-LATHE-07", "Optional"],
        ["operator_id", "OP-3", "Optional"],
    ], [CONTENT_W*0.40, CONTENT_W*0.38, CONTENT_W*0.22]))
    s.append(callout("tip",
        "Column names don't have to match exactly — the app auto-detects common variations. Duplicate rows "
        "are skipped, so re-uploading the same file is safe."))
    s.append(Paragraph("B.  Automatic feed from your MES / QMS  (hands-off)", S_H2))
    s.append(para(
        "IT enters your system's API details under <b>“Automatic data feed”</b> on the Connections page. The "
        "app then pulls new measurements on a schedule — no manual uploads.", S_BODY))
    s.append(Paragraph("C.  Live stream / push  (advanced)", S_H2))
    s.append(para(
        "For real-time machine feeds, your systems can stream measurements to the platform's data channel or "
        "push them to its API. Your IT team can set this up using the project's technical docs.", S_BODY))
    s.append(callout("info",
        "However the data arrives, it lands in one place and the <b>autonomous monitor analyses it "
        "automatically</b> — running SPC checks and raising alerts without anyone clicking “analyse.”"))

    # ---- 7. Part 5 Workspace ----
    s.append(h1("7", "Part 5 · Set up your quality workspace"))
    s.append(para("With data flowing, set up the things that match your shop floor. All of this is in the left sidebar.", S_LEAD))
    s.append(bullet("<b>Gage Registry</b> (Quality Tools): add your inspection gauges and fixtures with calibration status. Launch a GR&amp;R study for any gage in one click."))
    s.append(bullet("<b>GR&amp;R Studies</b> (Quality Tools): a guided three-step wizard. Type in measurements, paste a block straight from Excel, or click <b>Load sample</b> to try it. You get pass/fail results plus an AI review."))
    s.append(bullet("<b>SPC Monitor</b> (Monitor): live control charts per process. Standard rules (like the Nelson rules) flag out-of-control points; click a flagged point to see the rule, the recommended action, and to acknowledge it."))
    s.append(bullet("<b>Alert Rules</b> (Setup): decide which alerts reach which people or channel — e.g. send critical alerts to the night-shift Slack and email the rest. You connect the channels themselves in Part 3."))
    s.append(callout("tip",
        "Start small — add a couple of gages and one or two processes, confirm alerts reach you, then expand."))

    # ---- 8. Part 6 Test ----
    s.append(h1("8", "Part 6 · Test that everything works"))
    s.append(para("Run through this checklist to confirm the whole system works end-to-end. Tick each one.", S_LEAD))
    s.append(table([
        ["#", "Check", "How", "Looks right when…"],
        ["1", "Server connected", "Settings (gear)", "Green “Connected to your quality server”"],
        ["2", "You can sign in", "Open dashboard, log in", "Dashboard loads (your initials top-right)"],
        ["3", "Data is in", "Upload sample file on Connections", "“Added X of Y rows” confirmation"],
        ["4", "SPC is live", "Open SPC Monitor", "A control chart appears for your process"],
        ["5", "Alerts reach you", "Connect a channel → Send test", "Green “Working” badge + you receive it"],
        ["6", "A study runs", "GR&amp;R Studies → Load sample → Run", "Results + AI summary appear"],
        ["7", "Alerts show up", "Open Alert Inbox", "Active alerts listed (and counted on the bell)"],
        ["8", "Everything is logged", "Open Audit Trail", "Recent actions appear with time + actor"],
    ], [CONTENT_W*0.05, CONTENT_W*0.22, CONTENT_W*0.31, CONTENT_W*0.42]))
    s.append(callout("tip", "If all eight pass, the platform is fully working and ready to hand over."))

    # ---- 9. Troubleshooting ----
    s.append(h1("9", "Troubleshooting"))
    s.append(table([
        ["Problem", "Likely cause", "What to do"],
        ["Settings shows “Can't reach your quality server”", "Backend isn't running", "Ask IT to confirm Docker is up; re-run <font name='Courier-Bold'>docker compose up -d</font>"],
        ["“Test failed” on a channel", "Wrong value (webhook, password, token)", "Re-enter the value, Save changes, Send test again"],
        ["Uploaded a file but see no data", "Missing key columns", "Ensure the file has a timestamp, a part number and a measured value"],
        ["AI summaries are blank", "No Gemini key", "Add a Gemini key under “AI summaries” (optional feature)"],
        ["Dashboard won't open at all", "Wrong address, or app still starting", "Confirm http://localhost:3000 and that the install finished"],
    ], [CONTENT_W*0.34, CONTENT_W*0.26, CONTENT_W*0.40]))

    # ---- 10. Glossary ----
    s.append(h1("10", "Glossary"))
    s.append(table([
        ["Term", "In plain words"],
        ["SPC (Statistical Process Control)", "Live charts that watch a process and flag when it drifts outside normal limits"],
        ["GR&amp;R (Gage R&amp;R)", "A study that checks whether your gauge gives consistent, trustworthy readings"],
        ["Gage", "An inspection instrument — caliper, micrometer, CMM, and so on"],
        ["Control limits / Nelson rules", "Standard statistical rules used to decide a point is “out of control”"],
        ["Webhook", "A web link a service gives you so another app can post messages to it (e.g. Slack)"],
        ["API key / token", "A secret password that lets two systems talk to each other"],
        ["MES / QMS", "Your factory's Manufacturing Execution / Quality Management System"],
        ["Audit trail", "A tamper-proof log of every action, for traceability and audits"],
    ], [CONTENT_W*0.34, CONTENT_W*0.66]))

    # ---- 11. Quick reference ----
    s.append(h1("11", "Quick reference"))
    s.append(table([
        ["Action", "Where / command"],
        ["Open the dashboard", "http://localhost:3000"],
        ["Check the server is healthy", "http://localhost:8000/health/ready  →  “ready”"],
        ["Start the platform", "docker compose up --build -d"],
        ["Stop the platform", "docker compose down"],
        ["View server logs", "docker compose logs api"],
        ["Reopen the in-app tour", "“Getting started” (bottom-left of the sidebar)"],
        ["Confirm a tool works", "Connections → Send test → “Working”"],
    ], [CONTENT_W*0.36, CONTENT_W*0.64]))
    s.append(Spacer(1, 8))
    s.append(callout("info",
        "<b>In a sentence:</b> install once, connect your tools, bring in your data — and the platform "
        "watches quality for you, around the clock."))

    doc.build(s)
    return out


if __name__ == "__main__":
    path = build()
    print("WROTE", path, os.path.getsize(path), "bytes")
