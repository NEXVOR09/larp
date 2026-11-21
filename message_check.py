"""Message analyzer: finds common scam patterns in a pasted job offer, SMS or WhatsApp text.

Plain Python, no internet and no SerpApi credits needed.
"""
import html
import re

MAX_CHARS = 5000

EXAMPLE_MESSAGE = (
    "URGENT HIRING!! Work from home and earn Rs 5000 per day, no experience needed. "
    "Pay a refundable registration fee of Rs 1500 to confirm your slot. Limited slots, apply within 2 hours. "
    "Send your Aadhaar and bank account number on WhatsApp +91 9000000000 "
    "or mail hr.globaljobs@gmail.com. Join now: bit.ly/earn-now"
)

# (label, weight, regex, why it matters)
RULES = [
    (
        "Asks for money upfront", 30,
        r"(?:registration|joining|security|processing|training|kit|verification|refundable|activation|onboarding)"
        r"\s+(?:fee|fees|charge|charges|amount|deposit)|(?:pay|paying)\s+(?:a\s+)?(?:small\s+)?fee"
        r"|advance payment|upfront (?:fee|payment)",
        "Real employers never charge candidates to hire them.",
    ),
    (
        "Asks for sensitive details", 20,
        r"\botp\b|\bcvv\b|\bupi\s*pin\b|\bpassword\b|aadh?aa?r|\bpan\s*(?:card|number|no)\b"
        r"|bank account(?: number| details)?|account number|card number|net ?banking",
        "Scammers collect ID and bank details for fraud or identity theft.",
    ),
    (
        "Promises easy or guaranteed money", 20,
        r"guarantee(?:d)?\b|(?:earn|income|salary)\s+(?:up to\s+)?(?:₹|rs\.?|inr)?\s?\d[\d,]*\s*(?:/|per|a|each)\s*(?:day|daily|week|weekly|hour)"
        r"|daily (?:income|payment|payout|salary)|double your|100\s?% (?:profit|returns?|placement|job)"
        r"|no (?:experience|interview|skills|qualification)(?: needed| required)?",
        "Genuine jobs and investments do not promise fast, effortless money.",
    ),
    (
        "Creates urgency", 10,
        r"\burgent(?:ly)?\b|immediate(?:ly)?\b|today only|limited (?:slots|seats|vacanc(?:y|ies)|positions)"
        r"|last chance|hurry|within \d+ (?:hours?|hrs?|minutes?|mins?)|act now|don'?t miss",
        "Pressure to act fast is meant to stop you from checking.",
    ),
    (
        "Pushes you to a private chat app", 8,
        r"telegram|t\.me/|wa\.me/|whatsapp|signal app",
        "Many scams move the conversation to WhatsApp or Telegram.",
    ),
    (
        "Uses a free email address", 10,
        r"[\w.+-]+@(?:gmail|yahoo|outlook|hotmail|rediffmail|protonmail|ymail)\.[a-z.]+",
        "Companies normally email from their own domain, not a free address.",
    ),
    (
        "Uses a shortened link", 10,
        r"\b(?:bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|is\.gd|t\.co|goo\.gl|shorturl\.at)/\S*",
        "Short links hide where you are really going.",
    ),
    (
        "Offers simple online tasks for pay", 15,
        r"(?:like|subscribe|rate|review|follow)\s+(?:and\s+)?(?:youtube|videos?|products?|reels?|pages?|channels?)"
        r"|data entry|typing (?:job|work)|task[- ]based|copy[- ]paste (?:job|work)",
        "Task and typing jobs are a common cover for payment scams.",
    ),
    (
        "Mentions crypto or trading bait", 15,
        r"crypto(?:currency)?|bitcoin|\busdt\b|forex|trading signals?|investment plan|stock tips|binary options",
        "Investment bait is often used to take money, not to hire anyone.",
    ),
]

FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com", "protonmail.com", "ymail.com"}
SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd", "t.co", "goo.gl", "shorturl.at", "t.me", "wa.me"}

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(
    r"(?:https?://|www\.)[^\s)>\]]+"
    r"|\b(?:bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|is\.gd|t\.co|goo\.gl|shorturl\.at|t\.me|wa\.me)/[^\s)>\]]*"
    r"|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|co|net|org|io|xyz|info|online|site|shop|top|club|biz|app|link"
    r"|me|to|cc|store|tech|live|work|vip|page|space|website)\b(?:/[^\s)>\]]*)?",
    re.I,
)
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
AMOUNT = re.compile(r"(?:₹|rs\.?|inr)\s?\d[\d,]*", re.I)

VERDICTS = {
    "Low": "No common scam patterns found. Still verify the sender independently.",
    "Medium": "Some scam patterns found. Verify before you reply or pay.",
    "High": "Strong scam patterns found. Do not pay or share personal details.",
}


def level_for(score):
    if score < 20:
        return "Low"
    if score < 50:
        return "Medium"
    return "High"


def _domain_of(url):
    host = re.sub(r"^https?://", "", url.lower())
    host = re.sub(r"^www\.", "", host).split("/")[0]
    return host.rstrip(".,;:!?)")


def _unique(items):
    seen, out = set(), []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def highlight_html(text, spans):
    """The message as safe HTML with each suspicious part wrapped in <mark>."""
    spans = sorted(spans, key=lambda s: (s[0], -s[1]))
    merged = []
    for start, end, label in spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
            if label not in merged[-1][2]:
                merged[-1][2].append(label)
        else:
            merged.append([start, end, [label]])
    parts, pos = [], 0
    for start, end, labels in merged:
        parts.append(html.escape(text[pos:start]))
        title = html.escape(" · ".join(labels))
        parts.append(f'<mark title="{title}">{html.escape(text[start:end])}</mark>')
        pos = end
    parts.append(html.escape(text[pos:]))
    return "".join(parts).replace("\n", "<br>")


def analyze_message(text):
    """Return score, level, red flags, highlighted text and details found in the message."""
    text = (text or "")[:MAX_CHARS]
    flags, spans, total = [], [], 0
    for label, weight, pattern, why in RULES:
        matches = list(re.finditer(pattern, text, re.I))
        if not matches:
            continue
        total += weight
        examples = _unique([m.group(0).strip()[:60] for m in matches])[:3]
        flags.append({"label": label, "weight": weight, "why": why, "examples": examples})
        spans += [(m.start(), m.end(), label) for m in matches]

    emails = _unique(EMAIL.findall(text))
    no_email_text = EMAIL.sub(" ", text)
    urls = _unique([u.rstrip(".,;:!?)") for u in URL.findall(no_email_text)])
    phones = _unique([re.sub(r"\s+", " ", p).strip() for p in PHONE.findall(text)])
    amounts = _unique(AMOUNT.findall(text))

    # Websites worth looking up online (skip link shorteners and free email providers).
    domains = [_domain_of(u) for u in urls]
    domains += [e.split("@")[1].lower() for e in emails]
    domains = _unique([d for d in domains if d and d not in SHORTENERS and d not in FREE_EMAIL_DOMAINS])

    score = min(100, total)
    level = level_for(score)
    return {
        "score": score,
        "level": level,
        "verdict": VERDICTS[level],
        "flags": sorted(flags, key=lambda f: f["weight"], reverse=True),
        "highlighted": highlight_html(text, spans),
        "urls": urls,
        "emails": emails,
        "phones": phones,
        "amounts": amounts,
        "domains": domains,
        "truncated": len(text) >= MAX_CHARS,
    }
