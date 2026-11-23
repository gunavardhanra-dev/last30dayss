last30dayss

An API that finds recent discussion about a tech topic. It pulls from Hacker News and Stack Exchange, ranks everything into one list, and caches the results.

Live: https://last30dayss.onrender.com/docs

Free tier, so the first request after it's been idle takes about 50 seconds to wake up.

What it does

You give it a topic. It calls the Hacker News (Algolia) and Stack Exchange APIs, pulls the fields it needs from each, and converts both into the same shape. Then it scores every result on relevance, recency and engagement, and returns one ranked list.

Results get cached in Redis so the same search doesn't hit both APIs again.

Example
GET /search?topic=python
json
[
  {
    "source": "hackernews",
    "title": "Uv is the best thing to happen to the Python ecosystem in a decade",
    "url": "https://emily.space/posts/251023-uv",
    "points": 2214,
    "num_comments": 1324,
    "created_at_i": 1761482249,
    "engagement": 0.861,
    "recency": 0.367,
    "relevance": 0.667,
    "score": 3.596
  }
]
Architecture
  request ──▶ rate limit (10/min per IP)
                    │
                    ▼
              check Redis cache
                    │
            hit ────┴──── miss
             │             │
             │             ├──▶ Hacker News API
             │             ├──▶ Stack Exchange API
             │             ├──▶ normalise into one shape
             │             ├──▶ score and rank
             │             ├──▶ cache it (TTL 3600s + jitter)
             │             │
             ▼             ▼
            return ranked results

On Render this runs as two services: a Docker web service for the API, and a Key Value instance for the cache. Locally it's the same two containers under Docker Compose.

Design decisions
Scoring weights: relevance ×3, recency ×2, engagement ×1

Relevance gets the most weight because a post that isn't about what you searched for is useless no matter how popular it is.

Recency is next — the whole point is finding current discussion, so something from last week should beat something equally relevant from 2019.

Engagement counts least. Points and comments say something about quality, but if I weighted it higher the same few all-time-popular threads would show up for every search.

Two-pass normalisation

The raw numbers aren't comparable — HN points, Stack Exchange scores and Unix timestamps are three different scales. Adding them straight together would be meaningless, so each one gets scaled to 0–1 first.

That needs two passes, because you can't scale a value until you know the maximum, and you don't know the maximum until you've seen every result. First pass finds the max for each attribute, second pass scales everything and applies the weights.

I take the maxima across both sources together, not per source. The output is one ranked list, so results have to be comparable to each other — not just to other results from the same API.

Caching: cache-aside, 1 hour TTL

Check Redis first. On a miss, do the actual work, then write the result to the cache before returning it. The cache only fills from real traffic.

TTL is 3600 seconds. An hour felt right for this data — discussion on HN and Stack Exchange doesn't really change within an hour, so I lose almost no freshness, and repeated searches skip both API calls entirely.

Two additions on top of plain cache-aside:

Jitter. The TTL is 3600 plus a random 60–300 seconds. Without it, a burst of searches cached at the same moment all expire at the same moment, and every one of them stampedes the upstream APIs together.

Cache key normalisation. Keys are lowercased and stripped, so Python, python and " python" are one cache entry rather than three.

Protecting the upstream APIs

Two problems, both found after deploying.

Empty results weren't cached. Any query returning nothing — a typo, a nonsense string, a crawler — went straight through to both upstream APIs, every single time, because there was nothing to cache. Fixed by caching a sentinel value for empty results with a short TTL, so a repeated junk query is answered from Redis.

No rate limiting. /search was open, and each call fans out into two upstream requests. Added slowapi at 10 requests per minute per IP.

Failure behaviour

If Redis is down, the request still works. It logs a warning, treats it as a cache miss, and carries on to the APIs. The cache is an optimisation — it being unavailable isn't a reason to return a 500.

Same idea if one of the two sources fails: return results from the one that worked and tell the user the other was unavailable, instead of failing the whole request.

Config from the environment

Redis details come from REDIS_URL and the port from PORT, both with local defaults.

This is what makes it deployable. A hardcoded hostname only works on the machine it was built on. Reading from the environment means the same image talks to the redis container locally and Render's Key Value in production, with no code change.

Evaluating the ranking

I built an evaluation harness to check whether the ranking actually works, rather than assuming it did.

Method. 30 test topics covering specific technical queries, broad terms, ambiguous ones (go, rust, swift), niche topics, multi-word phrases and junk controls. Each query's top 10 results graded 0/1/2 for relevance — 0 unrelated, 1 related but not what was asked, 2 directly relevant. Grading done by an LLM judge (Gemini) against a written rubric, validated against my own blind hand-labels. Ranking quality measured with NDCG.

Baseline: NDCG 0.9029 across 24 topics. Six topics failed grading on API quota limits and are excluded.

Judge validation. 10/10 exact agreement with my blind hand-labels on postgres indexing. But repeated runs on rust ownership flipped 3 of 10 grades between identical calls — all on borderline titles. So: reliable on clear-cut cases, noisy on ambiguous ones.

What measuring found

Two bugs that were invisible without it.

Relevance was scoring 1 for every single result. The check was binary — does the query appear in the title — and both upstream APIs already filter by the query, so every result passed. The formula weighted relevance highest and was multiplying a constant. Rewritten as (query terms found in title) / (title length), normalised against the maximum in the result set.

Stack Exchange titles arrived HTML-encoded (&quot;, &lt;), which corrupted tokenisation and therefore the relevance score downstream. A data cleaning bug presenting as a ranking problem. Fixed with html.unescape at fetch time.

Neither would have surfaced from reading the code or eyeballing output.

Running it

With Docker:

bash
docker compose up --build

Then http://localhost:8000/docs

Without Docker (needs Redis running locally, otherwise every request is a cache miss):

bash
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate         # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload
Tests
bash
pytest

Five tests on the scoring engine — relevance, engagement and recency, plus an empty list and posts with a null title.

Known limitations

No date filter. The project is called last30days and nothing enforces a date range — Stack Exchange results from 2015 regularly surface. Recency is weighted in the score but never filtered at the fetch layer.

NDCG measures ordering, not retrieval. It scores how well the returned results are ordered, not whether good results were returned at all. A well-ordered list of mediocre links still scores high. The 0.90 baseline should be read with that in mind.

Synchronous requests inside async FastAPI. Both upstream calls block the event loop. Fine at one request at a time; not fine under concurrency.

Cross-source scale mismatch. HN point counts run an order of magnitude above Stack Exchange scores, and both are normalised against a shared maximum — so a maximum set by HN compresses every Stack Exchange result toward zero on the engagement axis.

Additive scoring admits irrelevant results. Because the three factors are summed, a result with zero relevance can still reach the top 5 on recency and engagement alone. A multiplicative or gated formula would fix this; untested so far.

Next
Date filter at the fetch layer, so the project does what its name says. Changes the result set, so it needs a re-grading pass against the eval harness.
A front end — the API returns per-factor scores for every result, and nothing currently shows them.
Semantic retrieval, as a separate project built on this eval harness: chunking, embeddings and hybrid search, measured against this keyword baseline rather than assumed to be better.