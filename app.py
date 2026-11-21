"""Trust Check web page. Run with:  python -m streamlit run app.py"""
import html
import os
import random
from urllib.parse import quote

import streamlit as st

from checker import SerpApiError, build_report, run_check

st.set_page_config(page_title="Trust Check", page_icon="🛡️", layout="wide")


def star_layers(count, seed, bright=False):
    """CSS for a field of stars at random spots (drawn once, no images needed)."""
    rnd = random.Random(seed)
    layers = []
    for _ in range(count):
        x, y = rnd.randint(1, 99), rnd.randint(1, 99)
        size = rnd.choice([2, 2.5, 3]) if bright else rnd.choice([1, 1, 1, 1.5, 2])
        alpha = rnd.choice([.8, .9, 1]) if bright else rnd.choice([.3, .45, .6, .8])
        layers.append(f"radial-gradient({size}px {size}px at {x}% {y}%, rgba(255,255,255,{alpha}), transparent 60%)")
    return ",".join(layers)


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html { color-scheme: dark; }
.stApp {
    background-color: #050816;
    background-image:
        radial-gradient(900px 520px at 86% -10%, rgba(99, 102, 241, .40), transparent 62%),
        radial-gradient(760px 480px at -8% 14%, rgba(14, 165, 233, .28), transparent 60%),
        radial-gradient(720px 440px at 62% 106%, rgba(168, 85, 247, .24), transparent 60%),
        linear-gradient(rgba(148, 163, 184, .045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, .045) 1px, transparent 1px),
        linear-gradient(180deg, #050816 0%, #0a1130 55%, #071a33 100%);
    background-size: auto, auto, auto, 56px 56px, 56px 56px, auto;
    background-attachment: fixed;
}
.stApp::before { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none; background-image: __STARS__; }
.stApp::after { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none; background-image: __SPARKLE__;
                animation: twinkle 5s ease-in-out infinite alternate; }
[data-testid="stHeader"] { background: transparent; }
.block-container { position: relative; z-index: 1; max-width: 1180px; padding-top: 3rem; padding-bottom: 4rem; }
#MainMenu, footer { visibility: hidden; }

.stApp, .stMarkdown, .stMarkdown p, .stApp label p, .stApp li {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; color: #e2e8f0;
}
[data-testid="stCaptionContainer"], .stCaption, .stApp small { color: #94a3b8; }

@keyframes rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes grow { from { width: 0; } }
@keyframes twinkle { from { opacity: .25; } to { opacity: 1; } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes drift { from { transform: translate(0, 0); } to { transform: translate(60px, 40px); } }

.bgorb { position: fixed; border-radius: 50%; filter: blur(80px); pointer-events: none; z-index: 0; animation: drift 24s ease-in-out infinite alternate; }
.bgorb.o1 { width: 380px; height: 380px; right: -80px; top: 18%; background: rgba(56, 189, 248, .22); }
.bgorb.o2 { width: 420px; height: 420px; left: -120px; bottom: 6%; background: rgba(139, 92, 246, .22); animation-duration: 30s; }

.hero { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 18px; }
.eyebrow { font-size: 12px; font-weight: 600; letter-spacing: .16em; color: #7dd3fc; text-transform: uppercase; margin-bottom: 8px; }
.title { font-size: 46px; font-weight: 700; letter-spacing: -.025em; line-height: 1.1; margin: 0 0 10px 0;
         background: linear-gradient(120deg, #ffffff 30%, #a5b4fc 70%, #7dd3fc); -webkit-background-clip: text; background-clip: text; color: transparent; }
.subtitle { font-size: 16px; color: #94a3b8; margin: 0; line-height: 1.6; max-width: 620px; }
.orbit { position: relative; width: 170px; height: 170px; flex: none; }
.orbit .ring { position: absolute; border-radius: 50%; border: 1px solid rgba(125, 211, 252, .35); }
.orbit .r1 { inset: 0; animation: spin 26s linear infinite; }
.orbit .r2 { inset: 24px; border-style: dashed; border-color: rgba(165, 180, 252, .4); animation: spin 18s linear infinite reverse; }
.orbit .r3 { inset: 46px; border-color: rgba(125, 211, 252, .2); }
.orbit .dot { position: absolute; width: 9px; height: 9px; border-radius: 50%; background: #7dd3fc; top: -4px; left: calc(50% - 4px); box-shadow: 0 0 14px #7dd3fc; }
.orbit .core { position: absolute; inset: 58px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px;
               background: radial-gradient(circle at 30% 30%, #7dd3fc, #6366f1); box-shadow: 0 0 40px rgba(99, 102, 241, .65); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 18px 0; }
.pill { font-size: 12px; font-weight: 500; color: #cbd5e1; padding: 5px 12px; border-radius: 999px;
        background: rgba(148, 163, 184, .1); border: 1px solid rgba(148, 163, 184, .2); }
.pill i { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #34d399; margin-right: 7px; box-shadow: 0 0 8px #34d399; }

/* ---- Streamlit widgets in dark glass ---- */
[data-baseweb="input"], [data-baseweb="base-input"] { background: rgba(15, 23, 42, .75) !important; border-radius: 12px !important; border-color: rgba(148, 163, 184, .28) !important; }
.stTextInput input { background: transparent !important; color: #f1f5f9 !important; font-size: 16px; padding: 12px 14px; }
.stTextInput input::placeholder { color: #64748b; }
.stTextInput button, .stTextInput svg { color: #94a3b8; }
[data-testid="stCheckbox"] p, [data-testid="stCheckbox"] span { color: #cbd5e1; }
.stFormSubmitButton button, .stDownloadButton button {
    background: linear-gradient(135deg, #38bdf8, #6366f1); border: 0; border-radius: 12px; padding: 9px 28px; font-weight: 600;
    box-shadow: 0 8px 24px rgba(99, 102, 241, .35);
}
.stFormSubmitButton button p, .stDownloadButton button p { color: #ffffff; }
.stFormSubmitButton button:hover, .stDownloadButton button:hover { filter: brightness(1.1); }
.stButton button[kind="secondary"], .stButton button[data-testid="stBaseButton-secondary"] {
    background: rgba(148, 163, 184, .1); border: 1px solid rgba(148, 163, 184, .3); border-radius: 12px; font-weight: 500;
}
.stButton button[kind="secondary"] p, .stButton button[data-testid="stBaseButton-secondary"] p { color: #e2e8f0; }
.stButton button[kind="secondary"]:hover, .stButton button[data-testid="stBaseButton-secondary"]:hover { border-color: #7dd3fc; }
[data-testid="stForm"] { border: 0; padding: 0; background: transparent; }
[data-testid="stExpander"] { background: rgba(15, 23, 42, .58); border: 1px solid rgba(148, 163, 184, .18); border-radius: 14px; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span { color: #e2e8f0; }
[data-testid="stExpander"] summary svg { color: #94a3b8; }
[data-testid="stSpinner"] p { color: #cbd5e1; }
.stTabs [data-baseweb="tab"] p { font-weight: 600; font-size: 15px; color: #94a3b8; }
.stTabs [aria-selected="true"] p { color: #f8fafc; }
.stTabs [data-baseweb="tab-highlight"] { background: #7dd3fc; }
.stTabs [data-baseweb="tab-border"] { background: rgba(148, 163, 184, .18); }

/* ---- Glass panels ---- */
.card, .panel, .pillar, .feat, .stepc, .vpanel {
    background: rgba(15, 23, 42, .58); border: 1px solid rgba(148, 163, 184, .18); border-radius: 16px;
    -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
    box-shadow: 0 10px 40px rgba(2, 6, 23, .45), inset 0 1px 0 rgba(255, 255, 255, .04);
    animation: rise .55s ease both;
}
.card { padding: 22px; margin: 20px 0 14px 0; }
.panel { padding: 20px; margin-bottom: 14px; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.ident { display: flex; align-items: center; gap: 14px; min-width: 0; }
.logo { width: 46px; height: 46px; border-radius: 12px; background: rgba(255, 255, 255, .95); padding: 7px; flex: none; object-fit: contain; }
.qname { font-size: 21px; font-weight: 700; letter-spacing: -.01em; color: #f8fafc; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.queried { font-size: 12px; color: #64748b; margin-bottom: 2px; }
.badge { font-size: 13px; font-weight: 600; padding: 5px 13px; border-radius: 999px; flex: none; border: 1px solid transparent; }
.badge.low { background: rgba(52, 211, 153, .14); color: #6ee7b7; border-color: rgba(52, 211, 153, .35); }
.badge.medium { background: rgba(251, 191, 36, .14); color: #fcd34d; border-color: rgba(251, 191, 36, .35); }
.badge.high { background: rgba(248, 113, 113, .15); color: #fca5a5; border-color: rgba(248, 113, 113, .35); }
.score { font-size: 32px; font-weight: 700; letter-spacing: -.02em; color: #f8fafc; flex: none; }
.score small { font-size: 15px; font-weight: 500; color: #64748b; margin-left: 2px; }
.bar { height: 7px; background: rgba(148, 163, 184, .15); border-radius: 999px; margin: 18px 0 14px 0; overflow: hidden; }
.bar div { height: 100%; border-radius: 999px; animation: grow .9s ease-out; }
.bar.low div { background: linear-gradient(90deg, #10b981, #34d399); }
.bar.medium div { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar.high div { background: linear-gradient(90deg, #ef4444, #f87171); }
.verdict { font-size: 15px; color: #cbd5e1; margin: 0; }
.conf { font-size: 12px; color: #94a3b8; margin-top: 10px; }
.conf b { color: #e2e8f0; }

.pillars { display: flex; gap: 12px; margin-bottom: 4px; }
.pillar { flex: 1; padding: 14px 16px; min-width: 0; }
.pl { font-size: 11px; font-weight: 600; letter-spacing: .1em; color: #94a3b8; text-transform: uppercase; }
.pn { font-size: 24px; font-weight: 700; color: #f8fafc; margin: 6px 0 2px 0; }
.pn.good { color: #6ee7b7; } .pn.warn { color: #fcd34d; } .pn.bad { color: #fca5a5; }
.ps { font-size: 12px; color: #94a3b8; }

.section { font-size: 12px; font-weight: 600; letter-spacing: .14em; color: #7dd3fc; text-transform: uppercase; margin: 28px 0 10px 0; }
.ptitle { font-size: 12px; font-weight: 600; letter-spacing: .14em; color: #94a3b8; text-transform: uppercase; margin: 0 0 14px 0; }
.item { padding: 12px 0; border-bottom: 1px solid rgba(148, 163, 184, .12); }
.item:last-child { border-bottom: 0; }
.item a, .voice a { color: #e2e8f0; font-weight: 500; text-decoration: none; border-bottom: 1px solid rgba(148, 163, 184, .4); }
.item a:hover, .voice a:hover { color: #7dd3fc; border-color: #7dd3fc; }
.item .meta, .voice .meta { font-size: 13px; color: #94a3b8; margin-top: 4px; line-height: 1.5; }
.tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px; background: rgba(148, 163, 184, .16); color: #cbd5e1; margin-right: 6px; }
.empty { font-size: 14px; color: #64748b; padding: 6px 0; line-height: 1.5; }
.more { font-size: 13px; color: #94a3b8; padding-top: 10px; }

.twocol { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.vpanel { padding: 16px 18px; }
.vpanel .vt { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.vpanel.pos .vt { color: #6ee7b7; } .vpanel.neg .vt { color: #fca5a5; } .vpanel.cur .vt { color: #7dd3fc; } .vpanel.frm .vt { color: #c4b5fd; }
.voice { padding: 10px 0; border-bottom: 1px solid rgba(148, 163, 184, .12); font-size: 14px; }
.voice:last-child { border-bottom: 0; }
.site { display: inline-block; font-size: 11px; font-weight: 600; color: #7dd3fc; margin-bottom: 4px; }

.photos { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.tile { display: block; text-decoration: none; min-width: 0; }
.tile img { width: 100%; height: 104px; object-fit: cover; border-radius: 12px; border: 1px solid rgba(148, 163, 184, .2); display: block; background: #0f172a; }
.tile span { display: block; font-size: 11px; color: #94a3b8; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.donut-wrap { display: flex; align-items: center; gap: 20px; }
.donut { width: 132px; height: 132px; border-radius: 50%; position: relative; flex: none; box-shadow: 0 0 30px rgba(99, 102, 241, .25); }
.hole { position: absolute; top: 20px; left: 20px; right: 20px; bottom: 20px; background: #0b1230; border-radius: 50%;
        display: flex; flex-direction: column; align-items: center; justify-content: center; }
.hole .n { font-size: 24px; font-weight: 700; line-height: 1; color: #f8fafc; }
.hole .l { font-size: 11px; color: #94a3b8; margin-top: 3px; }
.legend { flex: 1; min-width: 0; }
.leg { display: flex; align-items: center; justify-content: space-between; font-size: 13px; padding: 5px 0; color: #cbd5e1; }
.leg .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 8px; }
.leg b { color: #f8fafc; }

.topic { margin-bottom: 12px; }
.topic:last-child { margin-bottom: 0; }
.trow { display: flex; justify-content: space-between; font-size: 13px; color: #cbd5e1; margin-bottom: 6px; }
.trow b { color: #f8fafc; }
.tbar { height: 6px; background: rgba(148, 163, 184, .15); border-radius: 999px; overflow: hidden; }
.tbar div { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #6366f1, #7dd3fc); animation: grow .9s ease-out; }

.kv { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid rgba(148, 163, 184, .12); font-size: 14px; }
.kv:last-child { border-bottom: 0; }
.kv .k { color: #94a3b8; }
.kv .v { color: #f1f5f9; font-weight: 600; text-align: right; }
.kv .v.good { color: #6ee7b7; } .kv .v.bad { color: #fca5a5; }
.sub { font-size: 12px; color: #64748b; margin-top: 6px; line-height: 1.5; }
.about { font-size: 13px; color: #cbd5e1; line-height: 1.6; margin-bottom: 8px; }
.about b { color: #f8fafc; }
.about a { color: #7dd3fc; }

.tip { font-size: 14px; color: #cbd5e1; padding: 7px 0 7px 18px; position: relative; line-height: 1.5; }
.tip:before { content: ""; position: absolute; left: 0; top: 15px; width: 6px; height: 6px; border-radius: 50%; background: #7dd3fc; box-shadow: 0 0 8px #7dd3fc; }
.disclaimer { font-size: 12px; color: #64748b; margin-top: 22px; line-height: 1.5; }

.splitbar { display: flex; height: 8px; border-radius: 999px; overflow: hidden; margin: 8px 0 6px 0; background: rgba(148, 163, 184, .15); }
.splitbar i { display: block; height: 100%; }
.esum { font-size: 14px; color: #cbd5e1; }
.esum b { color: #f8fafc; }

.cmp { display: grid; grid-template-columns: 1.1fr 1fr 1fr; }
.cmp > div { padding: 11px 10px; border-bottom: 1px solid rgba(148, 163, 184, .12); font-size: 14px; min-width: 0; word-break: break-word; }
.cmp .ch { font-weight: 700; color: #f8fafc; font-size: 15px; }
.cmp .ck { color: #94a3b8; }
.cmp .cv { color: #f1f5f9; font-weight: 600; }
.cmpverdict { font-size: 15px; color: #f1f5f9; line-height: 1.55; }

.features { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 30px; }
.feat { flex: 1 1 30%; min-width: 230px; padding: 20px; }
.ico { width: 40px; height: 40px; border-radius: 11px; display: flex; align-items: center; justify-content: center; font-size: 19px; margin-bottom: 14px; background: rgba(99, 102, 241, .22); }
.ft { font-size: 15px; font-weight: 600; color: #f8fafc; margin-bottom: 4px; }
.fd { font-size: 13px; color: #94a3b8; line-height: 1.55; }
.how { display: flex; gap: 14px; flex-wrap: wrap; }
.stepc { flex: 1; min-width: 220px; padding: 16px 18px; display: flex; align-items: center; gap: 14px; font-size: 14px; color: #cbd5e1; }
.num { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #38bdf8, #6366f1); color: #ffffff; font-size: 13px; font-weight: 600;
       display: flex; align-items: center; justify-content: center; flex: none; }

@media (max-width: 760px) {
    .photos { grid-template-columns: repeat(2, 1fr); } .orbit { display: none; } .title { font-size: 34px; }
    .twocol { grid-template-columns: 1fr; } .pillars { flex-direction: column; }
}
</style>
"""
st.markdown(
    CSS.replace("__STARS__", star_layers(70, 11)).replace("__SPARKLE__", star_layers(16, 5, bright=True)),
    unsafe_allow_html=True,
)
st.markdown('<div class="bgorb o1"></div><div class="bgorb o2"></div>', unsafe_allow_html=True)

SENTIMENT_COLORS = {"positive": "#34d399", "neutral": "#fbbf24", "negative": "#f87171"}

NEXT_STEPS = {
    "Low": [
        "Read the return and refund policy before you pay.",
        "Prefer a payment method that offers buyer protection.",
    ],
    "Medium": [
        "Open the warning links and read what people actually say.",
        "Check the website address for lookalike spellings.",
        "Pay with a method you can dispute, not a direct bank transfer.",
    ],
    "High": [
        "Do not pay or share personal or bank details.",
        "If you already did, call your bank right away.",
        "In India, report cyber fraud at cybercrime.gov.in or call 1930.",
    ],
}

HOW_SCORE_WORKS = (
    "We search Google, Reddit, Google News and Google Maps for the name you entered. A result only counts if it "
    "mentions that name. Each result with a warning word (scam, fraud, fake, phishing...) adds 10 points, or 5 if it "
    "came from the dedicated scam search. Each reassuring result (official, verified...) removes 5. The score is capped "
    "between 0 and 100: under 20 is Low, 20 to 49 is Medium, 50 and above is High. Customer sentiment and employee "
    "opinions are estimated by counting praise and complaint words in review and discussion snippets, so they are a "
    "rough guide, not a verdict. Confidence shows how many results mentioned the name."
)


def esc(text):
    """Make text from the web safe to show inside our HTML."""
    return "" if text is None else html.escape(str(text))


def safe_link(url):
    return url if str(url).startswith(("http://", "https://")) else "#"


def link_item(hit, show_words=False):
    words = ""
    if show_words:
        words = "".join(f'<span class="tag">{esc(w)}</span>' for w in hit["words"])
    snippet = f'<div class="meta">{esc(hit["snippet"])}</div>' if hit.get("snippet") else ""
    return (
        f'<div class="item"><div>{words}<a href="{esc(safe_link(hit["link"]))}" target="_blank">'
        f'{esc(hit["title"])}</a></div>{snippet}</div>'
    )


def news_item(hit):
    meta = " · ".join(x for x in (hit.get("source"), hit.get("date")) if x)
    meta_html = f'<div class="meta">{esc(meta)}</div>' if meta else ""
    return (
        f'<div class="item"><div><a href="{esc(safe_link(hit["link"]))}" target="_blank">'
        f'{esc(hit["title"])}</a></div>{meta_html}</div>'
    )


def voice_item(v):
    site = f'<div class="site">{esc(v.get("site") or "web")}</div>'
    snippet = f'<div class="meta">{esc(v["snippet"])}</div>' if v.get("snippet") else ""
    return f'<div class="voice">{site}<div><a href="{esc(safe_link(v["link"]))}" target="_blank">{esc(v["title"])}</a></div>{snippet}</div>'


def voice_panel(title, css, voices, empty):
    body = "".join(voice_item(v) for v in voices) or f'<div class="empty">{esc(empty)}</div>'
    return f'<div class="vpanel {css}"><div class="vt">{esc(title)}</div>{body}</div>'


def logo_html(domain):
    if not domain:
        return ""
    src = f"https://www.google.com/s2/favicons?domain={quote(domain)}&sz=128"
    return f'<img class="logo" src="{esc(src)}" alt="">'


def summary_card(result):
    level = result["level"].lower()
    low_conf = " Few results mention this name, so treat the score with caution." if result["confidence"] == "Low" else ""
    conf = (
        f'<div class="conf">Confidence: <b>{esc(result["confidence"])}</b> · '
        f'{result["relevant"]} results mention the name.{esc(low_conf)}</div>'
    )
    return (
        f'<div class="card">'
        f'<div class="row"><div class="ident">{logo_html(result["domain"])}'
        f'<div style="min-width:0"><div class="queried">Trust check for</div>'
        f'<div class="qname">{esc(result["query"])}</div></div></div>'
        f'<span class="badge {level}">{esc(result["level"])} risk</span></div>'
        f'<div class="bar {level}"><div style="width:{result["score"]}%"></div></div>'
        f'<div class="row"><p class="verdict">{esc(result["verdict"])}</p>'
        f'<span class="score">{result["score"]}<small>/ 100</small></span></div>{conf}</div>'
    )


def pillars_html(result):
    warn = len(result["red_hits"])
    tone = {"Low": "good", "Medium": "warn", "High": "bad"}[result["level"]]
    voices = result["voices"]
    if voices["pct_positive"] is None:
        sat, sat_sub, sat_tone = "Unknown", "not enough reviews found", ""
    else:
        pct = voices["pct_positive"]
        sat = f"{pct}%"
        sat_tone = "good" if pct >= 60 else "warn" if pct >= 35 else "bad"
        sat_sub = f"positive across {voices['total']} voices"
    if result["places"]:
        top = result["places"][0]
        pres = "Found"
        pres_sub = f"Google Maps{' · ' + str(top['rating']) + ' ★' if top['rating'] else ''}"
        pres_tone = "good"
    else:
        pres, pres_sub, pres_tone = "Not found", "no Google Maps listing", ""
    return (
        '<div class="pillars">'
        f'<div class="pillar"><div class="pl">Scam evidence</div><div class="pn {tone}">{esc(result["level"])}</div>'
        f'<div class="ps">{warn} warning mentions</div></div>'
        f'<div class="pillar"><div class="pl">Customers like it</div><div class="pn {sat_tone}">{esc(sat)}</div>'
        f'<div class="ps">{esc(sat_sub)}</div></div>'
        f'<div class="pillar"><div class="pl">Real-world presence</div><div class="pn {pres_tone}">{esc(pres)}</div>'
        f'<div class="ps">{esc(pres_sub)}</div></div>'
        '</div>'
    )


def donut_html(voices):
    """A donut chart drawn with plain CSS, so it needs no extra packages."""
    breakdown = voices["breakdown"]
    if breakdown:
        stops, start = [], 0
        for item in breakdown:
            end = start + item["pct"]
            stops.append(f"{SENTIMENT_COLORS[item['key']]} {start}% {end}%")
            start = end
        gradient = ", ".join(stops)
    else:
        gradient = "rgba(148,163,184,.25) 0% 100%"
    legend = "".join(
        f'<div class="leg"><span><span class="dot" style="background:{SENTIMENT_COLORS[i["key"]]}"></span>'
        f'{esc(i["name"])}</span><b>{i["pct"]}%</b></div>'
        for i in breakdown
    ) or '<div class="empty">No customer reviews or discussions found.</div>'
    return (
        f'<div class="panel"><div class="ptitle">Do people enjoy using it?</div><div class="donut-wrap">'
        f'<div class="donut" style="background: conic-gradient({gradient})">'
        f'<div class="hole"><div class="n">{voices["total"]}</div><div class="l">voices</div></div></div>'
        f'<div class="legend">{legend}</div></div></div>'
    )


def topics_html(topics):
    """The complaint bars. Hidden when there is nothing to show."""
    if not topics:
        return ""
    rows = "".join(
        f'<div class="topic"><div class="trow"><span>{esc(t["name"])}</span><b>{t["pct"]}%</b></div>'
        f'<div class="tbar"><div style="width:{t["pct"]}%"></div></div></div>'
        for t in topics
    )
    return f'<div class="panel"><div class="ptitle">What people complain about</div>{rows}</div>'


def kv(key, value, tone=""):
    return f'<div class="kv"><span class="k">{esc(key)}</span><span class="v {tone}">{esc(value)}</span></div>'


def about_html(result):
    parts = []
    about = result["about"]
    if about:
        head = esc(about["title"])
        kind = f" · {esc(about['type'])}" if about["type"] else ""
        desc = esc(about["description"][:320])
        site = ""
        if str(about["website"]).startswith(("http://", "https://")):
            site = f' <a href="{esc(about["website"])}" target="_blank">{esc(about["website"])}</a>'
        parts.append(f'<div class="about"><b>{head}</b>{kind}<br>{desc}{site}</div>')
    elif result["top_results"]:
        parts.append(
            '<div class="sub" style="margin:0 0 6px 0">No company profile found. Top results for the name:</div>'
            + "".join(
                f'<div class="item"><a href="{esc(safe_link(r["link"]))}" target="_blank">{esc(r["title"])}</a>'
                f'<div class="meta">{esc(r["site"])}</div></div>'
                for r in result["top_results"]
            )
        )
    places = result["places"]
    if places:
        top = places[0]
        parts.append(kv("Google Maps listing", "Found", "good"))
        if top["type"]:
            parts.append(kv("Business type", top["type"]))
        if top["rating"]:
            reviews = f" ({top['reviews']} reviews)" if top["reviews"] else ""
            parts.append(kv("Rating", f"{top['rating']} ★{reviews}"))
        if top["address"]:
            parts.append(kv("Address", top["address"]))
        if top["phone"]:
            parts.append(kv("Phone", top["phone"]))
    else:
        parts.append(kv("Google Maps listing", "Not found"))
        note = result["maps_note"] or (
            "Online-only businesses may not have a listing, but a company that takes your money should be easy to identify."
        )
        parts.append(f'<div class="sub">{esc(note)}</div>')
    if result["domain"]:
        parts.append(kv("Website", result["domain"]))
    return f'<div class="panel"><div class="ptitle">About and how it operates</div>{"".join(parts)}</div>'


def ratings_html(ratings):
    """Star ratings other sites show. Hidden when Google showed none."""
    if not ratings:
        return ""
    rows = "".join(
        f'<div class="kv"><span class="k"><a href="{esc(safe_link(r["link"]))}" target="_blank" style="color:#cbd5e1">{esc(r["site"])}</a> '
        f'<span class="tag">{esc(r["kind"])}</span></span>'
        f'<span class="v">{esc(r["rating"])} ★'
        + (f' <span style="color:#94a3b8;font-weight:400">({int(r["reviews"]):,})</span>' if r["reviews"] else "")
        + "</span></div>"
        for r in ratings
    )
    return f'<div class="panel"><div class="ptitle">Ratings across the web</div>{rows}</div>'


def steps_html(level):
    tips = "".join(f'<div class="tip">{esc(t)}</div>' for t in NEXT_STEPS[level])
    return f'<div class="panel"><div class="ptitle">What to do next</div>{tips}</div>'


def photos_html(result):
    """Up to 4 pictures: the Google Maps photo first, then image search results."""
    tiles = []
    if result["places"]:
        thumb = result["places"][0].get("thumbnail", "")
        if str(thumb).startswith(("http://", "https://")):
            tiles.append({"src": thumb, "caption": "Google Maps", "link": ""})
    for img in result["images"]:
        tiles.append({"src": img["src"], "caption": img["title"] or img["source"], "link": img["link"]})
    tiles = tiles[:4]
    if not tiles:
        return ""
    cells = []
    for t in tiles:
        inner = (
            f'<img src="{esc(t["src"])}" alt="{esc(t["caption"])}" loading="lazy" referrerpolicy="no-referrer">'
            f'<span>{esc(t["caption"])}</span>'
        )
        if str(t["link"]).startswith(("http://", "https://")):
            cells.append(f'<a class="tile" href="{esc(t["link"])}" target="_blank">{inner}</a>')
        else:
            cells.append(f'<div class="tile">{inner}</div>')
    return f'<div class="section">What the web shows</div><div class="photos">{"".join(cells)}</div>'


def employees_html(emp):
    head = '<div class="section">What employees say</div>'
    if emp["total"] == 0:
        note = emp["note"] or "No employee reviews or discussions mentioning this company were found in the top results."
        return head + f'<div class="panel"><div class="empty">{esc(note)}</div></div>'
    counts = emp["counts"]
    total = max(emp["total"], 1)
    bar = "".join(
        f'<i style="width:{100 * counts[k] / total:.1f}%;background:{SENTIMENT_COLORS[k]}"></i>'
        for k in ("positive", "neutral", "negative")
    )
    if emp["pct_positive"] is not None:
        summary = f'<b>{emp["pct_positive"]}%</b> of {emp["total"]} employee mentions are positive.'
    else:
        summary = f'{emp["total"]} employee mentions found, too few to measure sentiment.'
    top = f'<div class="panel"><div class="esum">{summary}</div><div class="splitbar">{bar}</div></div>'
    empty_cur = "No clearly labelled posts from current employees in the top results."
    empty_frm = "No clearly labelled posts from former employees in the top results."
    two = (
        '<div class="twocol">'
        + voice_panel("Current employees", "cur", emp["current"], empty_cur)
        + voice_panel("Former employees", "frm", emp["former"], empty_frm)
        + "</div>"
    )
    other = ""
    if emp["other"]:
        other = (
            '<div class="section" style="margin-top:18px">More from review sites and discussions</div>'
            f'<div class="panel">{"".join(voice_item(v) for v in emp["other"])}</div>'
        )
    return head + top + two + other


@st.cache_data(show_spinner=False, ttl=3600)
def cached_check(query, key, include_employees):
    """Same question twice = no extra credits (handy during the demo)."""
    return run_check(query, key, include_employees)


def landing_html():
    """Shown before a search, so the page never looks empty."""
    feats = [
        ("🛡️", "Scam evidence", "Fraud and scam reports from across Google, scored from Low to High."),
        ("💬", "What customers say", "Reviews and Reddit discussions, split into praise and complaints."),
        ("📉", "What goes wrong", "The most common complaints: refunds, delivery, support, fakes and more."),
        ("🏢", "How it operates", "Company profile, Google Maps listing, address and star ratings."),
        ("👥", "Employee voices", "What current and former employees say on Reddit, Glassdoor and more."),
        ("📰", "Live news", "Recent headlines, so you see what is happening right now."),
    ]
    cards = "".join(
        f'<div class="feat"><div class="ico">{i}</div><div class="ft">{esc(t)}</div><div class="fd">{esc(d)}</div></div>'
        for i, t, d in feats
    )
    return (
        f'<div class="features">{cards}</div>'
        '<div class="section">How it works</div>'
        '<div class="how">'
        '<div class="stepc"><span class="num">1</span>Enter a website or company name</div>'
        '<div class="stepc"><span class="num">2</span>We scan Google, Reddit, news and maps live</div>'
        '<div class="stepc"><span class="num">3</span>You get a verdict with the evidence</div>'
        '</div>'
        '<div class="section">Powered by SerpApi</div>'
        '<div class="chips"><span class="pill"><i></i>Google Search API</span><span class="pill"><i></i>Google News API</span>'
        '<span class="pill"><i></i>Google Maps API</span><span class="pill"><i></i>Google Images API</span></div>'
    )


# ---------- Tab 1: check one website or company ----------
def render_single(api_key):
    with st.form("check_form"):
        query = st.text_input(
            "What do you want to check?",
            placeholder="Website or company name, for example example.com",
            label_visibility="collapsed",
        )
        include_employees = st.checkbox("Also show what current and former employees say (2 extra credits)", value=True)
        submitted = st.form_submit_button("Check")

    if submitted:
        if not api_key:
            st.error("Add your SerpApi key above first.")
        elif not query.strip():
            st.error("Type something to check first.")
        else:
            try:
                with st.spinner("Scanning the web..."):
                    st.session_state["result"] = cached_check(query.strip(), api_key, bool(include_employees))
            except SerpApiError as err:
                st.session_state["result"] = None
                st.error(f"SerpApi problem: {err}")

    result = st.session_state.get("result")
    if not result:
        st.markdown(landing_html(), unsafe_allow_html=True)
        return

    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(summary_card(result), unsafe_allow_html=True)
        st.markdown(pillars_html(result), unsafe_allow_html=True)

        photos = photos_html(result)
        if photos:
            st.markdown(photos, unsafe_allow_html=True)

        st.markdown('<div class="section">What customers say</div>', unsafe_allow_html=True)
        voices = result["voices"]
        st.markdown(
            '<div class="twocol">'
            + voice_panel("What people like", "pos", voices["positive"], "No clearly positive reviews found in the top results.")
            + voice_panel("What people complain about", "neg", voices["negative"], "No clearly negative reviews found in the top results.")
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section">Warning signs</div>', unsafe_allow_html=True)
        if result["red_hits"]:
            shown = result["red_hits"][:5]
            extra = len(result["red_hits"]) - len(shown)
            more = f'<div class="more">+ {extra} more in All sources below</div>' if extra > 0 else ""
            st.markdown("".join(link_item(h, show_words=True) for h in shown) + more, unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No warning words found in the top results.</div>', unsafe_allow_html=True)

        news = result["sections"].get("News", [])[:3]
        if news:
            st.markdown('<div class="section">In the news</div>', unsafe_allow_html=True)
            st.markdown("".join(news_item(n) for n in news), unsafe_allow_html=True)

    with right:
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        st.markdown(donut_html(result["voices"]), unsafe_allow_html=True)
        for block in (topics_html(result["topics"]), about_html(result), ratings_html(result["ratings"]), steps_html(result["level"])):
            if block:
                st.markdown(block, unsafe_allow_html=True)

    if result["employees"]:
        st.markdown(employees_html(result["employees"]), unsafe_allow_html=True)

    st.markdown('<div class="section">All sources</div>', unsafe_allow_html=True)
    for label, items in result["sections"].items():
        with st.expander(f"{label} ({len(items)})"):
            if items:
                st.markdown("".join(link_item(i) for i in items), unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty">No results.</div>', unsafe_allow_html=True)
    with st.expander("How the score works"):
        st.markdown(f'<div class="fd">{esc(HOW_SCORE_WORKS)}</div>', unsafe_allow_html=True)

    st.download_button("Download report", build_report(result), file_name="trust_check_report.txt")
    st.markdown(
        '<div class="disclaimer">A quick screening based on public search results, not proof. '
        'Always read the sources yourself before trusting or rejecting anything.</div>',
        unsafe_allow_html=True,
    )


# ---------- Tab 2: compare two ----------
def cmp_pos(r):
    pct = r["voices"]["pct_positive"]
    return "not enough data" if pct is None else f"{pct}% positive"


def cmp_rating(r):
    ratings = [x for x in r["ratings"] if x["kind"] == "Customer"] or r["ratings"]
    return f"{ratings[0]['rating']} ★ ({ratings[0]['site']})" if ratings else "none shown"


def cmp_complaint(r):
    return r["topics"][0]["name"] if r["topics"] else "none found"


def compare_verdict(a, b):
    diff = a["score"] - b["score"]
    if abs(diff) < 10:
        text = "Too close to call: their risk scores are within 10 points of each other."
    else:
        safer, other = (b, a) if diff > 0 else (a, b)
        text = f"{safer['query']} shows fewer warning signs (risk {safer['score']} against {other['score']})."
    if "Low" in (a["confidence"], b["confidence"]):
        text += " One of them has little data online, so treat this with caution."
    return text


def compare_html(a, b):
    def row(label, va, vb):
        return f'<div class="ck">{esc(label)}</div><div class="cv">{esc(va)}</div><div class="cv">{esc(vb)}</div>'

    rows = (
        '<div class="ch"></div>'
        f'<div class="ch">{esc(a["query"])}</div><div class="ch">{esc(b["query"])}</div>'
        + row("Risk level", f"{a['level']} ({a['score']}/100)", f"{b['level']} ({b['score']}/100)")
        + row("Customers like it", cmp_pos(a), cmp_pos(b))
        + row("Warning mentions", len(a["red_hits"]), len(b["red_hits"]))
        + row("Top complaint", cmp_complaint(a), cmp_complaint(b))
        + row("Google Maps listing", "Found" if a["places"] else "Not found", "Found" if b["places"] else "Not found")
        + row("Rating on other sites", cmp_rating(a), cmp_rating(b))
        + row("Confidence", a["confidence"], b["confidence"])
    )
    return (
        f'<div class="panel"><div class="ptitle">Which looks safer?</div>'
        f'<div class="cmpverdict">{esc(compare_verdict(a, b))}</div></div>'
        f'<div class="panel"><div class="ptitle">Side by side</div><div class="cmp">{rows}</div></div>'
    )


def render_compare(api_key):
    st.markdown(
        '<div class="subtitle" style="margin: 18px 0 14px 0">Weighing two shops or services? '
        'Enter both and see them side by side. This uses 14 credits.</div>',
        unsafe_allow_html=True,
    )
    with st.form("compare_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            name_a = st.text_input("First", key="cmp_a", placeholder="First website or company", label_visibility="collapsed")
        with col_b:
            name_b = st.text_input("Second", key="cmp_b", placeholder="Second website or company", label_visibility="collapsed")
        go = st.form_submit_button("Compare")

    if go:
        if not api_key:
            st.error("Add your SerpApi key above first.")
        elif not name_a.strip() or not name_b.strip():
            st.error("Enter both names to compare.")
        else:
            try:
                with st.spinner("Scanning both..."):
                    st.session_state["compare_pair"] = (
                        cached_check(name_a.strip(), api_key, False),
                        cached_check(name_b.strip(), api_key, False),
                    )
            except SerpApiError as err:
                st.session_state["compare_pair"] = None
                st.error(f"SerpApi problem: {err}")

    pair = st.session_state.get("compare_pair")
    if not pair:
        return
    a, b = pair
    st.markdown(compare_html(a, b), unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown(summary_card(a), unsafe_allow_html=True)
        st.markdown(pillars_html(a), unsafe_allow_html=True)
    with col_b:
        st.markdown(summary_card(b), unsafe_allow_html=True)
        st.markdown(pillars_html(b), unsafe_allow_html=True)


# ---------- Page ----------
st.markdown(
    '<div class="hero"><div>'
    '<div class="eyebrow">Trust Check</div>'
    '<div class="title">Can you trust this website?</div>'
    '<div class="subtitle">Enter any website or company. We check scam reports, what real customers and '
    'employees say, how the business operates, and tell you what we found.</div>'
    '</div><div class="orbit"><div class="ring r1"><span class="dot"></span></div><div class="ring r2"></div>'
    '<div class="ring r3"></div><div class="core">🛡️</div></div></div>'
    '<div class="chips"><span class="pill"><i></i>Live Google data</span><span class="pill"><i></i>Reddit voices</span>'
    '<span class="pill"><i></i>News</span><span class="pill"><i></i>Maps</span></div>',
    unsafe_allow_html=True,
)

default_key = os.environ.get("SERPAPI_KEY", "")
with st.expander("SerpApi key", expanded=not default_key):
    api_key = st.text_input("SerpApi key", type="password", value=default_key, label_visibility="collapsed")
    st.caption("A check uses 7 SerpApi searches, or 9 with employee voices. Repeat checks are free for an hour.")

tab_single, tab_compare = st.tabs(["Check a website", "Compare two"])
with tab_single:
    render_single(api_key)
with tab_compare:
    render_compare(api_key)
