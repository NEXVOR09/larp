"""Trust checker logic (plain Python, no UI, so it is easy to test).

Question it answers: can a customer trust this website or company?

Flow: ask SerpApi for search results, Reddit discussions, news, Google Maps and
images (and optionally employee reviews) -> look for warning words, praise and
complaints -> turn that into a risk score, customer sentiment and evidence.
"""
import re
from urllib.parse import urlparse

import requests

SERPAPI_URL = "https://serpapi.com/search.json"

# Words that suggest people are reporting a scam or a problem (used for the risk score).
RED_FLAGS = [
    "scam", "fraud", "fake", "cheat", "complaint", "phishing", "blacklist",
    "warning", "beware", "not legit", "arrested", "lost money", "ponzi", "stolen",
]
# Words that suggest the result is reassuring.
GOOD_FLAGS = ["genuine", "verified", "trusted", "official"]

# Words used to tell whether a review or post is positive or negative.
POSITIVE_WORDS = [
    "great", "love", "excellent", "recommend", "amazing", "awesome", "satisfied", "happy", "reliable",
    "trusted", "trustworthy", "fast delivery", "easy to use", "good service", "good quality", "best",
    "worth it", "genuine", "helpful", "smooth", "fantastic", "perfect", "supportive", "good work life",
    "great culture", "friendly", "flexible", "learning", "growth", "fair pay", "good pay",
]
NEGATIVE_WORDS = [
    "scam", "fraud", "fake", "worst", "terrible", "horrible", "awful", "poor", "disappointed", "avoid",
    "cheat", "stolen", "rude", "unresponsive", "no response", "never received", "not received",
    "not delivered", "late delivery", "delayed", "no refund", "refund not", "refused refund", "complaint",
    "waste of", "useless", "misleading", "hidden charges", "overcharged", "harass", "toxic", "micromanag",
    "underpaid", "low salary", "laid off", "layoffs", "burnout", "long hours", "unpaid", "delayed salary",
    "bad management", "office politics", "bad experience", "bad",
]
NEGATED_RECOMMEND = re.compile(r"(?:do not|don't|dont|not|never|wouldn't|would not)\s+recommend", re.I)

# What people complain about (used for the complaint bars).
TOPICS = {
    "Refunds and payments": ["refund", "chargeback", "charged", "payment", "money back", "deducted", "billing",
                             "subscription", "overcharged", "hidden charges"],
    "Delivery and orders": ["delivery", "delivered", "shipping", "shipped", "tracking", "never received",
                            "not received", "delayed"],
    "Customer support": ["customer service", "customer care", "customer support", "support", "helpline",
                         "unresponsive", "no response", "rude"],
    "Quality and fakes": ["fake", "counterfeit", "quality", "damaged", "defective", "duplicate"],
    "Fraud and scams": ["scam", "fraud", "cheat", "phishing", "stolen", "ponzi"],
    "Privacy and spam": ["spam", "privacy", "data leak", "hacked", "account blocked", "personal data"],
}

CURRENT_PATTERNS = [
    "current employee", "i work at", "i work for", "i currently work", "currently working", "i'm working at",
    "i am working", "we work at",
]
FORMER_PATTERNS = [
    "former employee", "ex-employee", "ex employee", "i worked at", "i worked for", "i used to work",
    "i left", "when i left", "my last day", "laid off", "i resigned", "i quit",
]
EMPLOYER_SITES = ("glassdoor", "ambitionbox", "indeed", "comparably", "teamblind", "kununu", "naukri")

VERDICTS = {
    "Low": "Few warning signs found online.",
    "Medium": "Some warning signs found. Read the sources before you pay.",
    "High": "Several warning signs found. Be careful before paying or sharing details.",
}


def _compile(words):
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + ")", re.I)


POS_RE = _compile(POSITIVE_WORDS)
NEG_RE = _compile(NEGATIVE_WORDS)
TOPIC_RES = {name: _compile(words) for name, words in TOPICS.items()}


class SerpApiError(Exception):
    """Raised when SerpApi says something went wrong (bad key, no credits...)."""


def search_serpapi(params, api_key):
    """Call SerpApi once (costs 1 credit) and return the JSON answer."""
    full_params = dict(params)
    full_params["api_key"] = api_key
    try:
        response = requests.get(SERPAPI_URL, params=full_params, timeout=30)
    except requests.RequestException as err:
        raise SerpApiError(f"Could not reach SerpApi: {err}")
    try:
        data = response.json()
    except ValueError:
        raise SerpApiError(f"SerpApi sent a strange reply (HTTP {response.status_code}).")
    if "error" in data:
        # "Google hasn't returned any results" is not a real failure.
        if "hasn't returned any results" in str(data["error"]):
            return {}
        has_results = any(
            k in data for k in ("organic_results", "news_results", "local_results", "images_results", "knowledge_graph")
        )
        if not has_results:
            raise SerpApiError(str(data["error"]))
    return data


def _domain(url):
    host = urlparse(str(url or "")).netloc.lower()
    return re.sub(r"^www\.", "", host)


def _rating_of(item):
    """Star rating and review count shown in a Google result, if there is one."""
    snippet = item.get("rich_snippet") or {}
    for part in ("top", "bottom"):
        ext = (snippet.get(part) or {}).get("detected_extensions") or {}
        rating, reviews = ext.get("rating"), ext.get("reviews")
        if isinstance(rating, (int, float)) and 0 < rating <= 10:
            return rating, reviews if isinstance(reviews, (int, float)) else None
    return None, None


def _clean_results(items, source_key):
    """Keep only the fields we use from each raw result."""
    cleaned = []
    for item in items or []:
        source_name, date = "", ""
        if source_key == "news":
            source = item.get("source")
            source_name = source.get("name", "") if isinstance(source, dict) else str(source or "")
            snippet = item.get("snippet", "") or source_name
            date = str(item.get("date", "") or "").split(",")[0]
        else:
            snippet = item.get("snippet", "")
        rating, reviews = _rating_of(item)
        link = item.get("link", "")
        cleaned.append({
            "title": item.get("title", ""),
            "link": link,
            "snippet": snippet,
            "source": source_name,
            "date": date,
            "site": _domain(link),
            "rating": rating,
            "reviews": reviews,
        })
    return cleaned


def _clean_places(data):
    """Keep the top 3 Google Maps listings with the fields we show."""
    places = data.get("local_results") or []
    if isinstance(places, dict):
        places = places.get("places", [])
    if not places and data.get("place_results"):
        places = [data["place_results"]]
    cleaned = []
    for p in places[:3]:
        cleaned.append({
            "title": p.get("title", ""),
            "address": p.get("address", ""),
            "rating": p.get("rating"),
            "reviews": p.get("reviews"),
            "phone": p.get("phone", ""),
            "website": p.get("website") or (p.get("links") or {}).get("website") or "",
            "type": p.get("type", ""),
            "thumbnail": p.get("thumbnail", ""),
        })
    return cleaned


def _clean_images(data, query):
    """Keep up to 4 image results with a normal web thumbnail that clearly relate to the name."""
    keys = name_keys(query)
    cleaned = []
    for item in data.get("images_results") or []:
        thumb = item.get("thumbnail") or ""
        if not thumb.startswith(("http://", "https://")):
            continue
        label = f"{item.get('title', '')} {item.get('source', '')} {item.get('link', '')}".lower()
        if not any(k in label for k in keys):
            continue  # skip pictures that do not obviously relate to what was searched
        cleaned.append({
            "src": thumb,
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "source": item.get("source", ""),
        })
        if len(cleaned) == 4:
            break
    return cleaned


def _clean_about(kg):
    """The company profile Google shows for well-known names (may not exist)."""
    if isinstance(kg, dict) and (kg.get("title") or kg.get("description")):
        return {
            "title": str(kg.get("title", "")),
            "type": str(kg.get("type", "")),
            "description": str(kg.get("description", "")),
            "website": str(kg.get("website", "")),
        }
    return None


def guess_domain(query, places):
    """The website address of the thing checked, if we can tell (used for its logo)."""
    q = re.sub(r"^https?://", "", query.lower().strip())
    q = re.sub(r"^www\.", "", q).split("/")[0]
    if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", q):
        return q
    for place in places:
        site = place.get("website", "")
        if site:
            host = urlparse(site if "//" in site else "//" + site).netloc.lower()
            host = re.sub(r"^www\.", "", host)
            if host:
                return host
    return ""


def name_keys(query):
    """Spellings of the name we expect to see in a relevant result."""
    q = query.lower().strip()
    keys = {q}
    stem = re.sub(r"^https?://", "", q)
    stem = re.sub(r"^www\.", "", stem)
    stem = stem.split("/")[0]
    keys.add(stem)
    keys.add(re.sub(r"\.[a-z]{2,}(\.[a-z]{2})?$", "", stem))  # drop .com / .co.in
    return {k for k in keys if len(k) >= 3}


def _mentions(result, keys):
    return any(k in f"{result['title']} {result['snippet']}".lower() for k in keys)


def analyse_results(results, query, weight):
    """Count results that mention the name AND a warning (or reassuring) word."""
    keys = name_keys(query)
    red_hits, good_hits = [], []
    for r in results:
        text = f"{r['title']} {r['snippet']}".lower()
        if not any(k in text for k in keys):
            continue  # not about the thing the user asked about
        found_red = [w for w in RED_FLAGS if w in text]
        found_good = [w for w in GOOD_FLAGS if w in text]
        if found_red:
            red_hits.append({**r, "words": found_red, "weight": weight})
        elif found_good:
            good_hits.append({**r, "words": found_good, "weight": weight})
    return red_hits, good_hits


def score_from_hits(red_hits, good_hits):
    """Each warning result adds points, each reassuring one removes a few."""
    points = sum(10 * h["weight"] for h in red_hits) - sum(5 * h["weight"] for h in good_hits)
    score = max(0, min(100, round(points)))
    if score < 20:
        level = "Low"
    elif score < 50:
        level = "Medium"
    else:
        level = "High"
    return score, level


def confidence_level(relevant):
    """How much evidence the score rests on (number of results that mention the name)."""
    if relevant >= 8:
        return "High"
    if relevant >= 3:
        return "Medium"
    return "Low"


def _percentages(counts):
    """Whole percentages that add up to exactly 100."""
    total = sum(counts.values())
    if total == 0:
        return {}
    raw = {k: 100 * v / total for k, v in counts.items() if v > 0}
    pct = {k: int(share) for k, share in raw.items()}
    leftover = 100 - sum(pct.values())
    for k in sorted(raw, key=lambda key: raw[key] - pct[key], reverse=True)[:leftover]:
        pct[k] += 1
    return pct


def sentiment_of(text):
    """positive, negative or neutral, by counting praise and complaint words."""
    text = text.lower()
    negated = len(NEGATED_RECOMMEND.findall(text))
    text = NEGATED_RECOMMEND.sub(" ", text)
    pos = len(POS_RE.findall(text))
    neg = len(NEG_RE.findall(text)) + negated
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def collect_voices(results, query):
    """People's posts and reviews that mention the name, each with a sentiment."""
    keys = name_keys(query)
    seen, voices = set(), []
    for r in results:
        if not _mentions(r, keys) or r["link"] in seen:
            continue
        seen.add(r["link"])
        voices.append({**r, "sentiment": sentiment_of(f"{r['title']} {r['snippet']}")})
    return voices


def summarize_voices(voices):
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for v in voices:
        counts[v["sentiment"]] += 1
    total = len(voices)
    pct = _percentages(counts)
    breakdown = [
        {"key": k, "name": k.capitalize(), "pct": pct[k]} for k in ("positive", "neutral", "negative") if k in pct
    ]
    return {
        "total": total,
        "counts": counts,
        "pct_positive": round(100 * counts["positive"] / total) if total >= 3 else None,
        "breakdown": breakdown,
        "positive": [v for v in voices if v["sentiment"] == "positive"][:3],
        "negative": [v for v in voices if v["sentiment"] == "negative"][:3],
    }


def complaint_topics(results, query):
    """Which kinds of problems come up in results that contain complaint words."""
    keys = name_keys(query)
    counts = {name: 0 for name in TOPICS}
    seen = set()
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        if not _mentions(r, keys) or r["link"] in seen or not NEG_RE.search(text):
            continue
        seen.add(r["link"])
        for name, regex in TOPIC_RES.items():
            if regex.search(text):
                counts[name] += 1
    pct = _percentages(counts)
    items = [{"name": n, "pct": pct[n], "count": counts[n]} for n in pct]
    return sorted(items, key=lambda i: (i["pct"], i["count"]), reverse=True)


def role_of(text):
    text = text.lower()
    current = any(p in text for p in CURRENT_PATTERNS)
    former = any(p in text for p in FORMER_PATTERNS)
    if current and not former:
        return "current"
    if former and not current:
        return "former"
    return "other"


def analyse_employees(results, query):
    """What current and former employees say (from review sites and Reddit)."""
    entries = collect_voices(results, query)
    for e in entries:
        e["role"] = role_of(f"{e['title']} {e['snippet']}")
    summary = summarize_voices(entries)
    return {
        "checked": True,
        "total": len(entries),
        "pct_positive": summary["pct_positive"],
        "counts": summary["counts"],
        "current": [e for e in entries if e["role"] == "current"][:3],
        "former": [e for e in entries if e["role"] == "former"][:3],
        "other": [e for e in entries if e["role"] == "other"][:4],
        "note": "",
    }


def collect_ratings(sections, query):
    """Star ratings other sites show in Google results (one per site)."""
    keys = name_keys(query)
    best = {}
    for results in sections.values():
        for r in results:
            if r["rating"] is None or not r["site"] or not _mentions(r, keys):
                continue
            current = best.get(r["site"])
            if current is None or (r["reviews"] or 0) > (current["reviews"] or 0):
                best[r["site"]] = {
                    "site": r["site"],
                    "rating": r["rating"],
                    "reviews": r["reviews"],
                    "link": r["link"],
                    "kind": "Employer" if any(s in r["site"] for s in EMPLOYER_SITES) else "Customer",
                }
    return sorted(best.values(), key=lambda x: x["reviews"] or 0, reverse=True)[:5]


def run_check(query, api_key, include_employees=True):
    """Run the searches and return everything the page shows.

    Credits: 7 searches, plus 2 if include_employees is on.
    """
    query = query.strip()
    if not query:
        raise ValueError("Please type a company or website first.")

    searches = [
        # (label, SerpApi parameters, result list key, weight)
        ("About", {"engine": "google", "q": query, "num": 10}, "organic_results", 1.0),
        ("Customer reviews", {"engine": "google", "q": f"{query} reviews", "num": 10}, "organic_results", 1.0),
        ("Reddit discussions", {"engine": "google", "q": f"{query} site:reddit.com", "num": 10}, "organic_results", 1.0),
        ("Scam and fraud reports", {"engine": "google", "q": f"{query} scam OR fraud", "num": 10}, "organic_results", 0.5),
        ("News", {"engine": "google_news", "q": query}, "news_results", 1.0),
    ]

    all_red, all_good, sections, about = [], [], {}, None
    for label, params, key, weight in searches:
        data = search_serpapi(params, api_key)
        if label == "About":
            about = _clean_about(data.get("knowledge_graph"))
        results = _clean_results(data.get(key), "news" if key == "news_results" else "web")
        sections[label] = results
        red, good = analyse_results(results, query, weight)
        all_red += red
        all_good += good

    # Google Maps: does this thing exist as a real-world business?
    places, maps_note = [], ""
    try:
        places = _clean_places(search_serpapi({"engine": "google_maps", "q": query, "type": "search"}, api_key))
    except SerpApiError as err:
        maps_note = f"Business listing check unavailable: {err}"

    # Pictures for context (safe search on). A failure here never breaks the check.
    images = []
    try:
        images = _clean_images(
            search_serpapi({"engine": "google_images", "q": query, "safe": "active"}, api_key), query
        )
    except SerpApiError:
        pass

    # What current and former employees say (optional, 2 extra credits).
    employees = None
    if include_employees:
        emp_results = []
        emp_searches = [
            ("Employee reviews", {"engine": "google", "q": f"{query} employee reviews glassdoor OR ambitionbox OR indeed", "num": 10}),
            ("Employee discussions", {"engine": "google", "q": f'{query} "worked at" OR "work at" OR "ex-employee" site:reddit.com', "num": 10}),
        ]
        failures = 0
        for label, params in emp_searches:
            try:
                results = _clean_results(search_serpapi(params, api_key).get("organic_results"), "web")
            except SerpApiError:
                failures += 1
                continue
            sections[label] = results
            emp_results += results
        employees = analyse_employees(emp_results, query)
        if failures == len(emp_searches):
            employees["note"] = "Employee searches were unavailable."

    # Everything except the employee searches feeds the customer-facing numbers.
    customer_sections = ["About", "Customer reviews", "Reddit discussions", "Scam and fraud reports", "News"]
    scanned = sum(len(sections[s]) for s in customer_sections)
    relevant = sum(sum(1 for r in sections[s] if _mentions(r, name_keys(query))) for s in customer_sections)

    voices = summarize_voices(collect_voices(sections["Customer reviews"] + sections["Reddit discussions"], query))
    topics = complaint_topics(
        sections["Customer reviews"] + sections["Reddit discussions"] + sections["Scam and fraud reports"], query
    )

    score, level = score_from_hits(all_red, all_good)
    return {
        "query": query,
        "domain": guess_domain(query, places),
        "score": score,
        "level": level,
        "verdict": VERDICTS[level],
        "confidence": confidence_level(relevant),
        "relevant": relevant,
        "scanned": scanned,
        "red_hits": all_red,
        "good_hits": all_good,
        "voices": voices,
        "topics": topics,
        "about": about,
        "top_results": sections["About"][:3],
        "places": places,
        "maps_note": maps_note,
        "images": images,
        "ratings": collect_ratings(sections, query),
        "employees": employees,
        "sections": sections,
    }


def build_report(result):
    """A plain-text report the user can download and share."""
    v = result["voices"]
    lines = [
        f"Trust check report: {result['query']}",
        f"Risk level: {result['level']} ({result['score']}/100)",
        f"Confidence: {result['confidence']} ({result['relevant']} results mention the name)",
        result["verdict"],
        "",
        "Customer sentiment:",
    ]
    if v["total"]:
        lines += [f"- {item['name']}: {item['pct']}%" for item in v["breakdown"]]
        lines.append(f"- based on {v['total']} reviews and discussions")
    else:
        lines.append("- no reviews or discussions found")
    lines += ["", "What people complain about:"]
    lines += [f"- {t['name']}: {t['pct']}%" for t in result["topics"]] or ["- nothing specific found"]
    lines += ["", "Warning signs:"]
    if result["red_hits"]:
        lines += [f"- {h['title']} ({h['link']}) [{', '.join(h['words'])}]" for h in result["red_hits"]]
    else:
        lines.append("- none found in the top results")
    lines += ["", "Ratings on other sites:"]
    lines += [
        f"- {r['site']}: {r['rating']} stars" + (f" ({int(r['reviews']):,} reviews)" if r["reviews"] else "")
        for r in result["ratings"]
    ] or ["- none found"]
    lines += ["", "Business listings (Google Maps):"]
    if result["places"]:
        for p in result["places"]:
            rating = f"{p['rating']} stars, {p['reviews']} reviews" if p["rating"] else "no rating"
            lines.append(f"- {p['title']}, {p['address']} ({rating})")
    else:
        lines.append("- no listing found")
    emp = result["employees"]
    if emp and emp["checked"]:
        lines += ["", "What employees say:"]
        if emp["total"]:
            share = f"{emp['pct_positive']}% positive, " if emp["pct_positive"] is not None else ""
            lines.append(f"- {share}{emp['total']} mentions found")
            for label in ("current", "former"):
                lines += [f"- {label} employee: {e['title']} ({e['link']})" for e in emp[label]]
        else:
            lines.append("- no employee mentions found")
    lines += ["", "This is a quick screening based on search results, not proof."]
    return "\n".join(lines)
