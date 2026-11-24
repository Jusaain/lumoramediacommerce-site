#!/usr/bin/env python3
"""Static site generator for Lumora Media Commerce.

Reads page bodies from src/pages/*.html (first line: <!--META {json} -->),
wraps them in the shared layout and writes static index.html files,
including the mirror paths required by the published Google OAuth branding
(/app/, /overview/, /privacy/, /terms/).

Usage: python3 src/build.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "src" / "pages"
SITE = "https://www.lumoramediacommerce.com"
APP = "Lumora Media Commerce"
YEAR = "2026"

NAV = [
    ("platform", "/platform/", "Platform"),
    ("methodology", "/methodology/", "Methodology"),
    ("security", "/security/", "Security"),
    ("privacy", "/privacy-policy/", "Privacy Policy"),
    ("terms", "/terms-of-service/", "Terms"),
]

# ---------------------------------------------------------------- helpers

def esc(s):
    return html.escape(s, quote=False)


def tokenize(src, rules):
    """Single-pass highlighter: rules = [(regex, css_class_or_callable)]."""
    rx = re.compile("|".join(f"(?P<g{i}>{r})" for i, (r, _) in enumerate(rules)), re.S)
    out, pos = [], 0
    for m in rx.finditer(src):
        out.append(esc(src[pos:m.start()]))
        i = int(m.lastgroup[1:])
        cls = rules[i][1]
        tok = m.group(0)
        out.append(cls(tok) if callable(cls) else f'<span class="{cls}">{esc(tok)}</span>')
        pos = m.end()
    out.append(esc(src[pos:]))
    return "".join(out)


def hl_gaql(src):
    return tokenize(src, [
        (r"'[^']*'", "ts"),
        (r"\b(?:SELECT|FROM|WHERE|AND|ORDER BY|DESC|ASC|LIMIT|DURING|IN|BETWEEN|PARAMETERS)\b", "tk"),
        (r"(?<![\w.])\d+(?![\w])", "tn"),
    ])


def _json_str(tok):
    m = re.match(r'("(?:[^"\\]|\\.)*")(\s*:)?', tok)
    if m.group(2):
        return f'<span class="tp">{esc(m.group(1))}</span>{m.group(2)}'
    return f'<span class="ts">{esc(m.group(1))}</span>'


def hl_json(src):
    return tokenize(src, [
        (r'"(?:[^"\\]|\\.)*"(?:\s*:)?', _json_str),
        (r"-?\b\d+(?:\.\d+)?\b", "tn"),
        (r"\b(?:true|false|null)\b", "tk"),
    ])


def hl_http(src):
    s = esc(src)
    s = re.sub(r"^(GET|POST|DELETE)\b", r'<span class="tk">\1</span>', s, flags=re.M)
    s = re.sub(r"^([A-Za-z-]+):", r'<span class="tp">\1</span>:', s, flags=re.M)
    s = re.sub(r"^(#.*)$", r'<span class="tc">\1</span>', s, flags=re.M)
    return s


def hl_csv(src):
    lines = esc(src).split("\n")
    if lines:
        lines[0] = f'<span class="tp">{lines[0]}</span>'
    return "\n".join(lines)


HL = {"gaql": hl_gaql, "json": hl_json, "http": hl_http, "csv": hl_csv, "text": esc}


def code_blocks(body):
    def repl(m):
        lang, label, raw = m.group(1), m.group(2), m.group(3)
        raw = raw.strip("\n")
        return (f'<figure class="code"><figcaption class="code-head"><b>{label}</b><span>{lang.upper()}</span></figcaption>'
                f'<pre><code>{HL[lang](raw)}</code></pre></figure>')
    return re.sub(r'<pre data-lang="(\w+)" data-label="([^"]*)">\n?(.*?)</pre>', repl, body, flags=re.S)


# ---------------------------------------------------------------- SVG: seasonal chart

def smooth_path(pts):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def season_chart():
    north = [38, 46, 62, 78, 94, 100, 92, 70, 48, 34, 30, 32]
    south = [92, 74, 52, 36, 28, 24, 26, 32, 50, 72, 90, 100]
    x0, x1, y0, y1 = 44, 506, 18, 186
    step = (x1 - x0) / 11

    def pts(vals):
        return [(x0 + i * step, y1 - (v / 100) * (y1 - y0)) for i, v in enumerate(vals)]

    pn, ps = pts(north), pts(south)
    out = ['<svg class="season-chart" viewBox="0 0 520 222" role="img" aria-labelledby="sc-t sc-d">',
           '<title id="sc-t">Illustrative 12-month seasonal search-demand index</title>',
           '<desc id="sc-d">Sample index for a summer-apparel category: Northern hemisphere markets peak in June, Australia peaks in December.</desc>',
           '<defs><linearGradient id="scN" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f66c4" stop-opacity=".18"/><stop offset="1" stop-color="#2f66c4" stop-opacity="0"/></linearGradient></defs>']
    for g in (0, 25, 50, 75, 100):
        y = y1 - g / 100 * (y1 - y0)
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="#ebe6dd" stroke-width="1"/>')
        out.append(f'<text x="{x0 - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="10.5" fill="#8a919c" font-family="ui-monospace, Menlo, monospace">{g}</text>')
    for i, m in enumerate("JFMAMJJASOND"):
        out.append(f'<text x="{x0 + i * step:.1f}" y="210" text-anchor="middle" font-size="10.5" fill="#8a919c" font-family="ui-monospace, Menlo, monospace">{m}</text>')
    dn = smooth_path(pn)
    out.append(f'<path d="{dn} L{x1},{y1} L{x0},{y1} Z" fill="url(#scN)"/>')
    out.append(f'<path d="{dn}" fill="none" stroke="#1f4fa3" stroke-width="2.4" stroke-linecap="round"/>')
    out.append(f'<path d="{smooth_path(ps)}" fill="none" stroke="#c98a1e" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="1 0"/>')
    for (x, y), c in ((pn[5], "#1f4fa3"), (ps[11], "#c98a1e")):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#fff" stroke="{c}" stroke-width="2.2"/>')
    out.append(f'<text x="{pn[5][0]:.1f}" y="{pn[5][1] - 10:.1f}" text-anchor="middle" font-size="10.5" fill="#1f4fa3" font-family="ui-monospace, Menlo, monospace">Jun peak</text>')
    out.append(f'<text x="{ps[11][0] - 6:.1f}" y="{ps[11][1] - 10:.1f}" text-anchor="end" font-size="10.5" fill="#a5670f" font-family="ui-monospace, Menlo, monospace">AU Dec peak</text>')
    out.append('</svg>')
    return "".join(out)


# ---------------------------------------------------------------- SVG: architecture diagram

F_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
F_MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"


def node(x, y, w, h, step, title, lines, lh=24, first=100):
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#122a4b" stroke="#2c4a77"/>',
         f'<text x="{x + 20}" y="{y + 30}" font-family="{F_MONO}" font-size="11.5" fill="#3fc79a">{step}</text>',
         f'<text x="{x + 20}" y="{y + 56}" font-family="{F_SANS}" font-size="16.5" font-weight="600" fill="#ffffff">{esc(title)}</text>',
         f'<line x1="{x + 20}" x2="{x + w - 20}" y1="{y + 72}" y2="{y + 72}" stroke="#2c4a77"/>']
    for i, ln in enumerate(lines):
        o.append(f'<text x="{x + 20}" y="{y + first + i * lh}" font-family="{F_SANS}" font-size="13" fill="#b4c3d9">{esc(ln)}</text>')
    return "".join(o)


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#3fc79a" stroke-width="1.8" marker-end="url(#arr)"/>'


def region(x, y, w, h, label, foot, foot_y):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="none" stroke="#3b5a86" stroke-dasharray="5 6"/>'
            f'<text x="{x + 20}" y="{y + 30}" font-family="{F_MONO}" font-size="12" fill="#c3d3ef">{esc(label)}</text>'
            f'<text x="{x + 20}" y="{foot_y}" font-family="{F_MONO}" font-size="11" fill="#7f93b3">{esc(foot)}</text>')


DEFS = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#3fc79a"/></marker></defs>')


def arch_svg():
    h = ['<svg class="svg-h" viewBox="0 0 1136 372" role="img" aria-labelledby="ah-t ah-d">',
         '<title id="ah-t">Lumora Media Commerce data flow and security architecture</title>',
         '<desc id="ah-d">OAuth 2.0 with PKCE authorizes the single adwords scope; the Google Ads API v23 GoogleAdsService and KeywordPlanIdeaService return data over TLS to the normalization engine, which produces structured JSON and CSV reporting exports inside an access-controlled environment.</desc>',
         DEFS,
         region(8, 30, 572, 330, "Google identity & API infrastructure", "Official Google Ads REST API, v23", 344),
         region(598, 30, 530, 330, "Lumora Media Commerce environment", "Credentials isolated, file mode 0600", 344),
         node(28, 82, 222, 228, "01  AUTHORIZE", "OAuth 2.0 + PKCE",
              ["Google consent screen", "S256 code challenge", "Scope: auth/adwords", "Short-lived access tokens", "Revocable refresh token"]),
         node(304, 82, 252, 228, "02  QUERY", "Google Ads API v23",
              ["GoogleAdsService", "GAQL search, searchStream", "KeywordPlanIdeaService", "generateKeywordIdeas", "generateKeywordHistoricalMetrics"]),
         node(640, 82, 238, 228, "03  NORMALIZE", "Normalization engine",
              ["Micros to currency units", "USD · GBP · EUR · CHF · AUD", "Geo & language constants", "12-month seasonality index", "Break-even ROAS context"]),
         node(914, 82, 196, 228, "04  REPORT", "Reporting exports",
              ["Structured JSON", "CSV, UTF-8", "Per market & date", "Stored with 0600", "No third-party sharing"]),
         arrow(250, 196, 300, 196), arrow(556, 196, 636, 196), arrow(878, 196, 910, 196),
         '<rect x="572" y="172" width="48" height="18" rx="4" fill="#0b1a2f"/><rect x="556" y="203" width="80" height="18" rx="4" fill="#0b1a2f"/>',
         f'<text x="596" y="186" text-anchor="middle" font-family="{F_MONO}" font-size="11" fill="#3fc79a">HTTPS</text>',
         f'<text x="596" y="216" text-anchor="middle" font-family="{F_MONO}" font-size="11" fill="#7f93b3">TLS 1.2/1.3</text>',
         '</svg>']
    v = ['<svg class="svg-v" viewBox="0 0 360 930" width="360" role="img" aria-labelledby="av-t">',
         '<title id="av-t">Lumora Media Commerce data flow and security architecture</title>',
         DEFS,
         region(4, 8, 352, 452, "Google identity & API", "Official Google Ads REST API, v23", 446),
         region(4, 492, 352, 432, "Lumora Media Commerce", "Credentials isolated, file mode 0600", 910),
         node(20, 50, 320, 170, "01  AUTHORIZE", "OAuth 2.0 + PKCE",
              ["Consent screen, S256 code challenge", "Scope: auth/adwords only", "Short-lived access tokens", "Revocable refresh token"], lh=21, first=96),
         node(20, 250, 320, 170, "02  QUERY", "Google Ads API v23",
              ["GoogleAdsService: GAQL search", "KeywordPlanIdeaService:", "generateKeywordIdeas", "generateKeywordHistoricalMetrics"], lh=21, first=96),
         node(20, 536, 320, 170, "03  NORMALIZE", "Normalization engine",
              ["Micros to currency units", "USD · GBP · EUR · CHF · AUD", "Geo & language constants", "12-month seasonality index"], lh=21, first=96),
         node(20, 736, 320, 150, "04  REPORT", "Reporting exports",
              ["Structured JSON and CSV, UTF-8", "Per market & date partitions", "No third-party sharing"], lh=21, first=96),
         arrow(180, 220, 180, 246), arrow(180, 420, 180, 532), arrow(180, 706, 180, 732),
         '<rect x="190" y="460" width="134" height="20" rx="4" fill="#0b1a2f"/>',
         f'<text x="196" y="474" font-family="{F_MONO}" font-size="11" fill="#3fc79a">HTTPS · TLS 1.2/1.3</text>',
         '</svg>']
    return "".join(h) + "".join(v)


# ---------------------------------------------------------------- Dashboard preview

MARKETS = [
    # code, name, cur, spend, value, roas, cpc, ctr
    ("US", "United States", "USD", "$18,420", "$71,840", 3.90, "$0.74", "1.92%"),
    ("UK", "United Kingdom", "GBP", "£9,610", "£35,560", 3.70, "£0.52", "2.08%"),
    ("DE", "Germany", "EUR", "€12,280", "€41,750", 3.40, "€0.46", "1.71%"),
    ("CH", "Switzerland", "CHF", "5,930 CHF", "24,910 CHF", 4.20, "0.88 CHF", "1.64%"),
    ("AU", "Australia", "AUD", "A$7,140", "A$22,850", 3.20, "A$0.69", "1.85%"),
]


def dashboard():
    rows = []
    for code, name, cur, spend, val, roas, cpc, ctr in MARKETS:
        pct = min(100, roas / 4.5 * 100)
        rows.append(
            f'<tr><td><span class="mkt"><span class="mc">{code}</span>{name} <span class="cur">{cur}</span></span></td>'
            f'<td>{spend}</td><td class="hide-sm">{val}</td>'
            f'<td><span class="roas"><span class="bar"><i style="width:{pct:.0f}%"></i></span>{roas:.2f}</span></td>'
            f'<td class="hide-sm">{cpc}</td></tr>')
    kws = [
        ("linen dress", "US · 2840", "40,500", "$0.62–1.94", "$1.13", 87, "HIGH"),
        ("merino jumper", "UK · 2826", "14,800", "£0.41–1.28", "£0.77", 71, "HIGH"),
        ("leinenkleid damen", "DE · 2276", "22,200", "€0.28–0.91", "€0.49", 58, "MEDIUM"),
    ]
    cards = []
    for term, geo, vol, rng, cpc, idx, lvl in kws:
        cards.append(
            f'<div class="kw"><div class="kw-top"><span class="kw-term">{term}</span><span class="kw-geo">{geo}</span></div>'
            f'<div class="kw-stats"><div><span class="l">Avg. monthly</span><span class="v">{vol}</span></div>'
            f'<div><span class="l">Top-of-page bid</span><span class="v">{rng}</span></div>'
            f'<div><span class="l">Avg. CPC</span><span class="v">{cpc}</span></div></div>'
            f'<div class="comp"><div class="comp-track"><i style="width:{idx}%"></i></div>'
            f'<div class="comp-label"><span>competitionIndex {idx}</span><span>{lvl}</span></div></div></div>')
    return f'''<div class="dash" role="figure" aria-label="Illustrative reporting interface preview of Lumora Media Commerce">
  <div class="dash-bar">
    <div class="dash-title"><img src="/assets/logo.svg" alt="" width="22" height="22">Multi-market performance <span class="crumb">/ Shopping &amp; Search / Last 30 days</span></div>
    <div class="dash-tags"><span class="pill pill-amber"><span class="dot"></span>Illustrative Reporting Interface Preview</span><span class="pill">Sample values</span></div>
  </div>
  <div class="dash-body">
    <div class="kpis">
      <div class="kpi"><div class="k-label">Ad spend (USD equiv.)</div><div class="k-value">$59,870</div><div class="k-delta">+8.4%<span class="hide-sm"> vs. prior period</span></div></div>
      <div class="kpi"><div class="k-label">Conversion value</div><div class="k-value">$217,420</div><div class="k-delta">+12.1%<span class="hide-sm"> vs. prior period</span></div></div>
      <div class="kpi"><div class="k-label">Blended ROAS</div><div class="k-value">3.63</div><div class="k-delta">Break-even 2.50</div></div>
      <div class="kpi"><div class="k-label">Clicks</div><div class="k-value">86,310</div><div class="k-delta neg">−2.3%<span class="hide-sm"> vs. prior period</span></div></div>
    </div>
    <div class="dash-main">
      <div class="panel">
        <div class="panel-head"><h4>Google Shopping &amp; Search by market</h4><span>GAQL · campaign</span></div>
        <table class="mtable">
          <thead><tr><th>Market</th><th>Cost</th><th class="hide-sm">Conv. value</th><th>ROAS</th><th class="hide-sm">Avg. CPC</th></tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
      <div class="panel">
        <div class="panel-head"><h4>Seasonal search-demand index</h4><span>12 months</span></div>
        <div class="chart-legend"><span><i style="background:#1f4fa3"></i>US · UK · DE · CH</span><span><i style="background:#c98a1e"></i>AU (southern)</span></div>
        <div class="chart-wrap">{season_chart()}</div>
      </div>
    </div>
    <div class="kw-cards">{"".join(cards)}</div>
  </div>
  <div class="dash-note">Illustrative reporting interface preview with sample values for demonstration only. It does not show real advertiser data, customers or results.</div>
</div>'''


# ---------------------------------------------------------------- layout

def header(active):
    items = []
    for key, href, label in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    cur = ' aria-current="page"' if active == "contact" else ""
    desk = "".join(items) + f'<li class="nav-cta"><a href="/contact/"{cur}>Contact</a></li>'
    mob = "".join(items) + f'<li><a href="/contact/"{cur}>Contact</a></li>'
    return f'''<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap nav">
    <a class="brand" href="/"><img src="/assets/logo.svg" alt="" width="30" height="30">Lumora Media Commerce</a>
    <nav aria-label="Primary"><ul class="nav-links">{desk}</ul></nav>
    <details class="mnav">
      <summary aria-label="Open menu"><span class="bars" aria-hidden="true"></span>Menu</summary>
      <nav class="mnav-panel" aria-label="Mobile"><ul>{mob}</ul><p class="mnav-mail">info@lumoramediacommerce.com</p></nav>
    </details>
  </div>
</header>'''


FOOTER = f'''<footer class="site-footer">
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand">
        <a class="brand" href="/"><img src="/assets/logo.svg" alt="" width="30" height="30">Lumora Media Commerce</a>
        <p>Lumora Media Commerce is e-commerce advertising analytics and search-demand research software built on the official Google Ads API, operated by Lumora Media LLC.</p>
      </div>
      <div class="foot-col">
        <h4>Platform</h4>
        <ul>
          <li><a href="/">Overview</a></li>
          <li><a href="/platform/">Platform &amp; modules</a></li>
          <li><a href="/methodology/">Methodology</a></li>
          <li><a href="/security/">Security &amp; compliance</a></li>
        </ul>
      </div>
      <div class="foot-col">
        <h4>Legal</h4>
        <ul>
          <li><a href="/privacy-policy/">Privacy Policy</a></li>
          <li><a href="/terms-of-service/">Terms of Service</a></li>
          <li><a href="https://developers.google.com/terms/api-services-user-data-policy" rel="noopener">Google API Services User Data Policy</a></li>
          <li><a href="https://developers.google.com/terms" rel="noopener">Google APIs Terms of Service</a></li>
        </ul>
      </div>
      <div class="foot-col">
        <h4>Company</h4>
        <ul>
          <li><a href="/contact/">Contact &amp; company profile</a></li>
          <li><a href="mailto:info@lumoramediacommerce.com">info@lumoramediacommerce.com</a></li>
        </ul>
        <address>Lumora Media LLC<br>30 N Gould St Ste N<br>Sheridan, WY 82801<br>United States</address>
      </div>
    </div>
    <div class="foot-bottom">
      <p>&copy; {YEAR} Lumora Media LLC, a Wyoming limited liability company. Lumora Media Commerce is a product of Lumora Media LLC.</p>
      <p>Google, Google Ads and Google Shopping are trademarks of Google LLC. Lumora Media Commerce is an independent application and is not affiliated with or endorsed by Google.</p>
    </div>
  </div>
</footer>'''

JSONLD = json.dumps({
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "Organization", "@id": SITE + "/#org", "name": "Lumora Media LLC", "url": SITE + "/",
         "logo": SITE + "/assets/logo-120.png", "email": "info@lumoramediacommerce.com",
         "brand": {"@type": "Brand", "name": APP},
         "address": {"@type": "PostalAddress", "streetAddress": "30 N Gould St Ste N", "addressLocality": "Sheridan",
                     "addressRegion": "WY", "postalCode": "82801", "addressCountry": "US"}},
        {"@type": "SoftwareApplication", "name": APP, "applicationCategory": "BusinessApplication",
         "operatingSystem": "Web", "url": SITE + "/", "publisher": {"@id": SITE + "/#org"}},
    ],
}, separators=(",", ":"))


def page(meta, body):
    title = meta["title"]
    desc = meta["desc"]
    canon = SITE + meta["path"]
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="application-name" content="Lumora Media Commerce">
<meta name="description" content="{html.escape(desc)}">
<meta name="theme-color" content="#0c1e35">
<link rel="canonical" href="{canon}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/logo.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/logo-120.png">
<meta property="og:site_name" content="Lumora Media Commerce">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/assets/logo-120.png">
<link rel="stylesheet" href="/assets/styles.css">
<script type="application/ld+json">{JSONLD}</script>
</head>
<body>
{header(meta["nav"])}
<main id="main">
{body}
</main>
{FOOTER}
</body>
</html>
'''


def label_tables(body):
    """Add data-label attributes to dtable cells so they can stack on mobile."""
    def table(m):
        t = m.group(0)
        head = re.search(r"<thead>(.*?)</thead>", t, re.S)
        if not head:
            return t
        labels = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)]

        def row(rm):
            i = iter(labels)
            return re.sub(r"<(td|th)(?=[ >])", lambda c: f'<{c.group(1)} data-label="{html.escape(next(i, ""))}"', rm.group(0))
        tbody = re.sub(r"<tr>.*?</tr>", row, t.split("</thead>", 1)[1], flags=re.S)
        return t.split("</thead>", 1)[0] + "</thead>" + tbody
    return re.sub(r'<table class="dtable">.*?</table>', table, body, flags=re.S)


SCOPE = "<code>https://www.googleapis.com/auth/adwords</code>"


def main():
    built = []
    for f in sorted(PAGES.glob("*.html")):
        text = f.read_text()
        first, body = text.split("\n", 1)
        meta = json.loads(re.match(r"<!--META (.*) -->", first).group(1))
        body = body.replace("{{DASHBOARD}}", dashboard()).replace("{{ARCH}}", arch_svg())
        body = code_blocks(body)
        body = label_tables(body).replace(SCOPE, "<code>https://www.googleapis.com/<wbr>auth/adwords</code>")
        out = page(meta, body)
        for p in [meta["path"]] + meta.get("mirrors", []):
            target = ROOT / p.strip("/") / "index.html" if p != "/" else ROOT / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(out)
            built.append((p, len(out)))
    for p, n in built:
        print(f"{p:<22} {n:>7} bytes")


if __name__ == "__main__":
    main()
