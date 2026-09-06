# last30dayss

An API that finds recent discussion about a tech topic. It pulls from Hacker News and Stack Exchange, ranks everything into one list, and caches the results.

**Live:** https://last30dayss.onrender.com/docs

Free tier, so the first request after it's been idle takes about 50 seconds to wake up.

---

## What it does

You give it a topic. It calls the Hacker News (Algolia) and Stack Exchange APIs, pulls the fields it needs from each, and converts both into the same shape. Then it scores every result on relevance, recency and engagement, and returns one ranked list.

Results get cached in Redis so the same search doesn't hit both APIs again.

### Example

```
GET /search?topic=python
```

```json
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
    "relevance": 1,
    "score": 4.596
  }
]
```

---

## Architecture

```
  request ──▶ check Redis cache
                    │
            hit ────┴──── miss
             │             │
             │             ├──▶ Hacker News API
             │             ├──▶ Stack Exchange API
             │             ├──▶ normalise into one shape
             │             ├──▶ score and rank
             │             ├──▶ cache it (TTL 3600s)
             │             │
             ▼             ▼
            return ranked results
```

On Render this runs as two services: a Docker web service for the API, and a Key Value instance for the cache. Locally it's the same two containers under Docker Compose.

---

## Design decisions

### Scoring weights: relevance ×3, recency ×2, engagement ×1

Relevance gets the most weight because a post that isn't about what you searched for is useless no matter how popular it is.

Recency is next — the whole point is finding *current* discussion, so something from last week should beat something equally relevant from 2019.

Engagement counts least. Points and comments say something about quality, but if I weighted it higher the same few all-time-popular threads would show up for every search.

### Two-pass normalisation

The raw numbers aren't comparable — HN points, Stack Exchange scores and Unix timestamps are three different scales. Adding them straight together would be meaningless, so each one gets scaled to 0–1 first.

That needs two passes, because you can't scale a value until you know the maximum, and you don't know the maximum until you've seen every result. First pass finds the max for each attribute, second pass scales everything and applies the weights.

I take the maxima across both sources together, not per source. The output is one ranked list, so results have to be comparable to each other — not just to other results from the same API.

### Caching: cache-aside, 1 hour TTL

Check Redis first. On a miss, do the actual work, then write the result to the cache before returning it. The cache only fills from real traffic.

TTL is 3600 seconds. An hour felt right for this data — discussion on HN and Stack Exchange doesn't really change within an hour, so I lose almost no freshness, and repeated searches skip both API calls entirely.

### Failure behaviour

If Redis is down, the request still works. It logs a warning, treats it as a cache miss, and carries on to the APIs. The cache is an optimisation — it being unavailable isn't a reason to return a 500.

Same idea if one of the two sources fails: return results from the one that worked and tell the user the other was unavailable, instead of failing the whole request.

### Config from the environment

Redis details come from `REDIS_URL` and the port from `PORT`, both with local defaults.

This is what makes it deployable. A hardcoded hostname only works on the machine it was built on. Reading from the environment means the same image talks to the `redis` container locally and Render's Key Value in production, with no code change.

---

## Running it

With Docker:

```bash
docker compose up --build
```

Then http://localhost:8000/docs

Without Docker (needs Redis running locally, otherwise every request is a cache miss):

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate         # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## Tests

```bash
pytest
```

Five tests on the scoring engine — relevance, engagement and recency, plus an empty list and posts with a null title.

---

## Known limitations

<!-- TODO: two or three, your words, describing the code as it is now.
     You've already spotted two of these yourself:

     - Concurrency: `requests` is synchronous inside an async framework.
       What happens to the event loop when several searches come in at once?
     - Cross-source scale: HN point counts run much higher than Stack
       Exchange scores, and both are scaled against a shared maximum.
       Whose max sets the ceiling, and what does that do to SE results?
     - No rate limiting or auth on /search — what does that do to the
       upstream API quotas?
     - Cache keys: "Python" vs "python" vs " python".

     Anything you plan to build goes under "Next" instead.
-->

---

## Next

**Phase 2:** an LLM layer on top of the results — summarising what the discussion actually says, instead of just returning links.
