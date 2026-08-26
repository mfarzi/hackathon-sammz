"""Render the stakeholder deck as SVG slides in the product's own design language.

Palette and chrome are lifted from frontend/app/globals.css and the live UI:
NHS blue band, the six-stage rail, white cards with a left accent bar on
nhs-grey-5. Content is taken verbatim from frontend/lib/consultScript.ts so the
deck and the demo tell the same story with the same numbers.
"""

from pathlib import Path

OUT = Path("/Users/mfarzi/source/hackathon/docs/slides")
W, H = 1920, 1080

# NHS product palette, from globals.css
BLUE, DARK, BRIGHT = "#005eb8", "#003087", "#0072ce"
GREEN, RED, AMBER = "#007f3b", "#d5281b", "#8a6100"
AMBER_BG, GREEN_BG, RED_BG = "#fffcf2", "#f5fbf7", "#fdf2f1"
INK, G1, G2, G3, G4, G5 = "#212b32", "#4c6272", "#768692", "#aeb7bd", "#d8dde0", "#f0f4f5"
WHITE = "#ffffff"

STAGES = ["Case described", "Query fanned out", "Sites read own notes",
          "Follow-up asked", "Panel attacks", "Report returned"]

FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif'
MONO = '"SF Mono", Menlo, monospace'


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size=24, fill=INK, weight="400", font=FONT, track=None, anchor="start"):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    k = f' letter-spacing="{track}"' if track else ""
    return (f'<text x="{x}" y="{y}" font-family=\'{font}\' font-size="{size}" '
            f'fill="{fill}" font-weight="{weight}"{k}{a}>{esc(s)}</text>')


def rect(x, y, w, h, fill, rx=0, stroke=None, sw=1):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{st}/>'


def card(x, y, w, h, accent=BLUE, fill=WHITE, aw=6):
    """White panel with a left accent bar — the product's thread-message shape."""
    return (rect(x, y, w, h, fill, 4, G4, 1.2)
            + rect(x, y, aw, h, accent, 0))


def header(title="Rare Disease Consult Network",
           tagline="Ask fifty hospitals. Move no records.",
           right=None):
    o = [rect(0, 0, W, 96, BLUE), rect(0, 96, W, 6, DARK)]
    o += [rect(64, 26, 92, 44, WHITE, 3)]
    o += [txt(110, 58, "NHS", 30, BLUE, "700", track="1", anchor="middle")]
    o += [txt(180, 46, title, 32, WHITE, "700")]
    o += [txt(180, 76, tagline, 21, "#a8cbe8")]
    if right:
        for i, line in enumerate(right):
            o += [txt(W - 64, 46 + i * 26, line, 20, "#cfe3f4", anchor="end")]
    return "".join(o)


def rail(active):
    """The six-stage progress rail, mirroring the product's."""
    o = [rect(0, 102, W, 92, WHITE)]
    span = (W - 128) / 6
    for i, label in enumerate(STAGES):
        x = 64 + i * span
        done, now = i < active, i == active
        col = BLUE if now else (G2 if done else G3)
        mark = "  ✓" if done else ""
        o += [txt(x, 138, f"STAGE {i + 1}{mark}", 17, col, "700", track="1.2")]
        o += [txt(x, 168, label, 22, INK if now else (G1 if done else G3),
                  "700" if now else "400")]
    o += [rect(0, 192, W, 2, G4)]
    if active > 0:
        o += [rect(0, 190, 64 + active * span - 20, 4, GREEN)]
    o += [rect(64 + active * span - 20, 190, span, 4, BLUE)]
    return "".join(o)


def page(body, active=None, right=None, bg=G5):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         rect(0, 0, W, H, bg), header(right=right)]
    if active is not None:
        o.append(rail(active))
    o.append(body)
    o.append("</svg>")
    return "".join(o)


def eyebrow(x, y, s):
    return txt(x, y, s.upper(), 22, BLUE, "700", track="1.6")


def headline(x, y, s, size=62):
    return txt(x, y, s, size, INK, "700")


def wrap(x, y, s, width_chars, size=24, fill=INK, lh=34, weight="400", font=FONT):
    """Naive wrap — the copy is hand-fitted, this only guards long lines."""
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 <= width_chars:
            cur = f"{cur} {w_}".strip()
        else:
            lines.append(cur); cur = w_
    lines.append(cur)
    return "".join(txt(x, y + i * lh, l, size, fill, weight, font) for i, l in enumerate(lines))


def chip(x, y, label, fg, bg, w=None):
    w = w or (len(label) * 11 + 34)
    return (rect(x, y - 22, w, 32, bg, 16, fg, 1.2)
            + txt(x + 17, y, label.upper(), 17, fg, "700", track="1.1"))


def stat(x, y, big, cap, col=INK):
    return txt(x, y, big, 68, col, "700") + txt(x, y + 34, cap.upper(), 18, G2, "700", track="1.3")


# ---------------------------------------------------------------- 1. cover
def s1():
    o = [rect(0, 0, W, H, BLUE), rect(0, H - 12, W, 12, DARK)]
    o += [rect(160, 300, 148, 70, WHITE, 4),
          txt(234, 352, "NHS", 48, BLUE, "700", track="1.5", anchor="middle")]
    o += [txt(160, 520, "Rare Disease", 104, WHITE, "700"),
          txt(160, 630, "Consult Network", 104, WHITE, "700")]
    o += [txt(160, 720, "Ask fifty hospitals. Move no records.", 40, "#a8cbe8")]
    o += [txt(160, 900, "A clinician describes a patient nobody can place. Every hospital checks its own", 24, "#cfe3f4"),
          txt(160, 936, "records, reasons over its own notes, and answers — without a record leaving the building.", 24, "#cfe3f4")]
    o += [txt(160, 1010, "Track 1 · Flower Agent Harness   ·   Collaborative Agent Hackathon, Cambridge   ·   26 August 2026",
              20, "#7fb0da")]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}">' + "".join(o) + "</svg>")


# ------------------------------------------------------------- 2. the patient
def s2():
    o = [eyebrow(64, 258, "The case, as the clinician typed it")]
    o += [card(64, 292, 1792, 212, BLUE)]
    o += [txt(112, 372, "Man in his 40s, six weeks of nosebleeds and persistent nasal crusting,", 34, INK)]
    o += [txt(112, 420, "now coughing blood. Urine dip shows blood. Sinus pain throughout.", 34, INK)]
    o += [txt(112, 468, "Two courses of antibiotics, no response.", 34, INK)]
    o += [stat(64, 640, "6 weeks", "of symptoms"),
          stat(560, 640, "2 courses", "of antibiotics, no response"),
          stat(1160, 640, "0", "diagnoses reached", RED)]
    o += [headline(64, 810, "His hospital has never seen this combination.", 54)]
    o += [txt(64, 880, "One or two comparable cases in living memory, and no way to reach the ones sitting", 26, G1),
          txt(64, 918, "in a hospital two hundred miles away. The data that would settle it is patient records.", 26, G1)]
    return page("".join(o), active=0)


# --------------------------------------------------------------- 3. the network
def s3():
    sites = [("Royal Infirmary", "Urban teaching", "26,149"),
             ("Riverbend Rural", "District general", "5,203"),
             ("Cardiac Institute", "Specialist centre", "10,057"),
             ("Children's Hospital", "Paediatric", "11,532"),
             ("Regional Hospital", "Regional", "22,060")]
    o = [eyebrow(64, 258, "The network"), headline(64, 328, "Five hospitals. Seventy-five thousand records.")]
    for i, (name, kind, n) in enumerate(sites):
        x = 64 + i * 362
        o += [card(x, 400, 340, 176, GREEN)]
        o += [txt(x + 26, 448, name, 25, INK, "700")]
        o += [txt(x + 26, 480, kind, 20, G2)]
        o += [txt(x + 26, 540, n, 38, INK, "700"), txt(x + 26 + len(n) * 22, 540, "records", 20, G2)]
    o += [rect(64, 640, 1792, 1, G4)]
    o += [stat(64, 748, "6", "relevant cases in the whole network"),
          stat(700, 748, "4", "hospitals hold one or more"),
          stat(1300, 748, "3", "the most any single site holds", RED)]
    o += [headline(64, 906, "No one of them holds enough to make the call.", 50)]
    o += [txt(64, 968, "The answer already exists. It is distributed across institutions that cannot share records.", 26, G1)]
    return page("".join(o), active=1)


# ----------------------------------------------------- 4. what crosses the wire
def s4():
    o = [eyebrow(64, 258, "Stage 2 · what actually crosses the boundary"),
         headline(64, 328, "The query travels. The records don't.")]
    o += [card(64, 400, 880, 460, BLUE)]
    o += [chip(112, 460, "Sent to every hospital", BLUE, "#e8f1fa")]
    o += [txt(112, 528, "symptoms", 22, G1, "700", font=MONO)]
    for i, sym in enumerate(["epistaxis", "nasal_crusting", "haemoptysis", "haematuria", "sinus_pain"]):
        o += [txt(112, 570 + i * 40, "· " + sym, 26, INK, "400", font=MONO)]
    o += [txt(560, 528, "age_bracket", 22, G1, "700", font=MONO), txt(560, 570, "41-50", 26, INK, font=MONO)]
    o += [txt(560, 640, "gender", 22, G1, "700", font=MONO), txt(560, 682, "M", 26, INK, font=MONO)]
    o += [card(976, 400, 880, 460, RED, RED_BG)]
    o += [chip(1024, 460, "Never leaves the hospital", RED, WHITE)]
    for i, held in enumerate(["record_id", "the free-text clinical note", "anything identifying"]):
        o += [txt(1024, 552 + i * 52, "· " + held, 30, INK, "400", font=MONO if i == 0 else FONT)]
    o += [txt(1024, 748, "Read where they live, then dropped. An allowlist", 24, G1),
          txt(1024, 782, "decides what may cross, so a field added to the", 24, G1),
          txt(1024, 816, "record format later cannot leak by being forgotten.", 24, G1)]
    o += [headline(64, 950, "Sites return a judgement their own agent wrote — not a record it copied.", 40)]
    return page("".join(o), active=1)


# ------------------------------------------------------------ 5. sites answer
def s5():
    rows = [("Cardiac Institute", "No data", AMBER, AMBER_BG,
             "“Nothing combines upper airway disease with renal findings. Our corpus is cardiac — treat this as a genuine absence, not a gap in coverage.”"),
            ("Riverbend Rural", "1 case", GREEN, WHITE,
             "“Treated twice as sinusitis with no response, then frank haematuria. Referred out before a diagnosis was reached here, so our record ends unresolved.”"),
            ("Children's Hospital", "1 case", GREEN, WHITE,
             "“Saddle-nose deformity, microscopic haematuria on screening. Confirmed on biopsy. Argues against the alternatives: no anti-GBM antibodies.”"),
            ("Royal Infirmary", "2 cases", GREEN, WHITE,
             "“Upper airway disease preceded renal involvement by weeks in both. Both treated as infection first. Neither improved on antibiotics.”"),
            ("Regional Hospital", "3 cases", GREEN, WHITE,
             "“Two confirmed vasculitis; one turned out to be TB with incidental renal stones. We would not exclude TB on this presentation alone.”")]
    o = [eyebrow(64, 250, "Stage 3 · each site reads its own notes, locally"),
         headline(64, 316, "Five answers. One of them is “nothing”.", 54)]
    for i, (name, tag, col, bg, quote) in enumerate(rows):
        y = 372 + i * 132
        o += [card(64, y, 1792, 116, col, bg)]
        o += [txt(112, y + 44, name, 26, INK, "700")]
        o += [chip(112, y + 88, tag, col, WHITE if bg != WHITE else GREEN_BG)]
        o += [wrap(400, y + 44, quote, 96, 24, G1, 32)]
    return page("".join(o), active=2)


# ----------------------------------------------------------- 6. the follow-up
def s6():
    o = [eyebrow(64, 258, "Stage 4 · the hub asks a question back"),
         headline(64, 328, "This is where it stops being a search.")]
    o += [card(64, 400, 1792, 156, G3, WHITE)]
    o += [txt(112, 452, "“Three sites describe upper airway disease before renal involvement. That fits several", 26, G1),
          txt(112, 490, "vasculitides equally well, so it does not discriminate. What separates them is whether the", 26, G1)]
    o += [txt(112, 528, "renal picture is a true glomerulonephritis, and how fast it moved.”", 26, G1)]
    o += [rect(64, 566, 1792, 148, BLUE, 4)]
    o += [txt(112, 630, "“Did the renal involvement show an active urinary sediment, and how many", 34, WHITE, "700"),
          txt(112, 678, "weeks from first nasal symptom to renal finding?”", 34, WHITE, "700")]
    ans = [("Royal Infirmary", "Active sediment in both. 5 and 7 weeks."),
           ("Children's Hospital", "Active sediment. Roughly 9 weeks."),
           ("Regional Hospital", "Active sediment in the two confirmed cases; the TB mimic had a bland sediment.")]
    for i, (site, a) in enumerate(ans):
        y = 776 + i * 62
        o += [card(64, y, 1792, 50, GREEN)]
        o += [txt(112, y + 33, site, 23, INK, "700"), txt(480, y + 33, a, 23, G1)]
    o += [txt(64, 1010, "The mimic was excluded on the answer to a question no one had thought to ask at the start.",
              28, GREEN, "700")]
    return page("".join(o), active=3)


# --------------------------------------------------------------- 7. the panel
def s7():
    rows = [("Granulomatosis with polyangiitis", "0.87", "Survived", GREEN, GREEN_BG,
             "Held against all three refuters. Upper airway disease preceding active glomerulonephritis over weeks, unresponsive to antibiotics — matches 6 of 7 network cases."),
            ("Microscopic polyangiitis", "0.71", "Unverified", AMBER, AMBER_BG,
             "Only two reviewers returned a verdict before the round closed. Not read as agreement."),
            ("Anti-GBM disease", "0.68", "Killed 3–0", RED, RED_BG,
             "The Children's Hospital case tested negative for anti-GBM antibodies, and sinonasal disease preceding renal involvement by weeks does not fit the usual course."),
            ("Seasonal vasculitic nephropathy", "0.66", "Planted probe · killed 3–0", RED, RED_BG,
             "Not a real entity. Inserted indistinguishably to test whether the panel can still say no. Rejected for having no case series behind it at any site.")]
    o = [eyebrow(64, 250, "Stage 5 · five blind reviewers, then three refuters each"),
         headline(64, 316, "The panel attacks its own answer.", 56)]
    for i, (name, score, tag, col, bg, body) in enumerate(rows):
        y = 372 + i * 158
        o += [card(64, y, 1792, 142, col, bg)]
        o += [txt(112, y + 48, name, 30, INK, "700")]
        o += [txt(112, y + 92, score, 34, col, "700", font=MONO)]
        o += [chip(240, y + 88, tag, col, WHITE)]
        o += [wrap(700, y + 44, body, 84, 23, G1, 31)]
    o += [txt(64, 1032, "A panel that never rejects anything is a rubber stamp. The planted probe proves rejection is live on this run.",
              26, INK, "700")]
    return page("".join(o), active=4)


# -------------------------------------------------------------- 8. the report
def s8():
    o = [eyebrow(64, 258, "Stage 6 · what reaches the clinician"),
         headline(64, 328, "A lead to investigate. Not a diagnosis.")]
    o += [card(64, 400, 1792, 200, GREEN, GREEN_BG)]
    o += [txt(112, 470, "Granulomatosis with polyangiitis", 44, INK, "700")]
    o += [txt(112, 522, "0.87", 30, GREEN, "700", font=MONO)]
    o += [txt(220, 522, "top-3 mean  ·  6 cases across 4 sites  ·  no site held more than 3", 26, G1)]
    o += [txt(112, 570, "Survived refutation with dissent carried.", 26, INK, "700")]
    o += [card(64, 636, 880, 168, AMBER, AMBER_BG)]
    o += [chip(112, 692, "Dissent carried", AMBER, WHITE)]
    o += [txt(112, 740, "No site reported ANCA status, so serology is", 24, G1),
          txt(112, 774, "assumed rather than shown.", 24, G1)]
    o += [card(976, 636, 880, 168, G3, WHITE)]
    o += [chip(1024, 692, "Not claimed", G1, WHITE)]
    o += [txt(1024, 740, "No clinical validation. A symptom set is still", 24, G1),
          txt(1024, 774, "health information. Synthetic records throughout.", 24, G1)]
    o += [txt(64, 900, "It advises. It does not diagnose.", 54, INK, "700")]
    o += [txt(64, 990, "The note never moves. The judgement does.", 40, BLUE, "700")]
    return page("".join(o), active=5)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for i, fn in enumerate([s1, s2, s3, s4, s5, s6, s7, s8], start=1):
        p = OUT / f"slide-{i:02d}.svg"
        p.write_text(fn(), encoding="utf-8")
        print("wrote", p.name)
