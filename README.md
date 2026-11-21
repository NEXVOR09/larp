# Trust Check

**Can you trust this website or company?** Enter a name or a web address and Trust Check gathers live evidence from across the web, then shows it in one clear report.

Built for the Beyond 9TO5 Buildathon, Track 1: Best Use of SerpApi.

## The problem

Before paying a website or joining a company, people open many tabs: Google, Reddit, review sites, the news, Maps and employee review pages. Most people skip the research, and scams and bad experiences follow. Trust Check does that research in one step.

## What it shows

| Question | What Trust Check does |
| --- | --- |
| Is it a scam? | Scores scam and fraud evidence from Low to High, with the source links. |
| Do people enjoy using it? | Reads reviews and Reddit threads and splits them into positive, neutral and negative. |
| What goes wrong? | Groups complaints into themes: refunds and payments, delivery, support, fakes, fraud, privacy. |
| How does it operate? | Shows the company profile, Google Maps listing, address, phone and ratings other sites display. |
| What do employees say? | Finds posts from current and former employees on review sites and Reddit. |
| What is happening now? | Shows recent news headlines. |
| Which is safer? | The "Compare two" tab puts two websites side by side. |

Every claim links back to its source, and the report can be downloaded as a text file.

## SerpApi APIs used

- Google Search API (company profile, reviews, Reddit threads, scam reports, employee reviews)
- Google News API
- Google Maps API
- Google Images API

## Run it

1. Install Python 3 from python.org (tick "Add python.exe to PATH" during install).
2. Open a terminal in this folder and run: `pip install -r requirements.txt`
3. Run: `python -m streamlit run app.py`
4. Paste your SerpApi key in the page (or set the `SERPAPI_KEY` environment variable).

No key yet? Click **See a sample report** to preview the page with made-up data.

To test real searches and print a debugging summary, run `python selftest.py`.

## Files

- `app.py`: the web page (Streamlit)
- `checker.py`: searching, scoring and analysis
- `sample_data.py`: made-up data for the sample report
- `selftest.py`: runs real checks and prints a summary

## How the score works

A search result only counts if it mentions the name that was entered. Results with warning words add risk points, and reassuring results remove a few. Sentiment and complaint themes are estimated from word counts in review snippets, so they are a rough guide. A confidence label shows how many results mentioned the name.

## Limits

- It is a quick screening based on public search snippets, not proof.
- Small or new businesses have little online data, and the confidence label says so.
- Sentiment is estimated from keywords, so sarcasm or mixed reviews can be misjudged.
- Each check uses 7 SerpApi credits, or 9 with employee voices.

## Ideas for later

- Browser extension that warns while shopping
- More languages and country-specific scam reporting links
- Trend over time: is a site getting better or worse?
