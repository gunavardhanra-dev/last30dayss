from typing import Annotated
from fastapi import FastAPI, status, Depends, HTTPException, Request
import requests
import math as m
import time as t
import redis, json, logging

app = FastAPI()
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
# DECODE RESPONSE makes Redis return strings instead of raw bytes
logging.basicConfig(level=logging.INFO)
#configures logging once, says "show INFO level and above"
logger=logging.getlogger(__name__)


@app.get("/")
def homepage():
    return {"status": "ok"}


def fetch_hackernews(topic):
    url = f"http://hn.algolia.com/api/v1/search?query={topic}"
    response = requests.get(url)
    data = response.json()
    hits = data["hits"]
    results = []
    for hit in hits:
        results.append(
            {
                "title": hit["title"],
                "url": hit["url"],
                "points": hit["points"],
                "num_comments": hit["num_comments"],
                "created_at_i": hit["created_at_i"],
            }
        )
    return results


@app.get("/search")
def search(topic: str):
    if not topic:
        return {"error": "topic required"}
    key = f"search:{topic}"
    try:
        cached = r.get(key)
    except Exception as e:
        logger.warning(f"Redis GET failed: {e}")
        cached = None
    if cached:
        logger.info("Cache hit")
        return json.loads(cached)
    try:
        hn = fetch_hackernews(topic)
    except Exception as e:
        logger.warning(f"Hacker News fetch failed: {e}")
        hn = []
    try:
        se = fetch_stackexchange(topic)
    except Exception as e:
        logger.warning(f"Stack Exchange fetch failed: {e}")
        se = []
    combined = hn + se
    if not combined:
        return {"error": "no results available"}
    result = score_posts(combined, topic)
    try:
        r.setex(key, 3600, json.dumps(result))
    except Exception as e:
        logger.warning(f"redis SET failed:{e}")
    logger.info("Cache miss")
    return result


def score_posts(posts, topic):
    w_rel = 3
    w_eng = 2
    w_rec = 1
    max_engagement = float("-inf")
    max_recency = float("-inf")
    for post in posts:
        engagement = m.log(1 + post["points"] + post["num_comments"])
        age = t.time() - post["created_at_i"]
        recency = 1 / (age + 1)
        title = post["title"] or ""  # this is because some titles can be null
        if topic.lower() in title.lower():
            relevance = 1
        else:
            relevance = 0
        max_engagement = max(max_engagement, engagement)
        max_recency = max(max_recency, recency)
        post["engagement"] = engagement
        post["recency"] = recency
        post["relevance"] = relevance
    for post in posts:
        post["engagement"] = post["engagement"] / max_engagement
        post["recency"] = post["recency"] / max_recency
        score = (
            (w_rel * post["relevance"])
            + (w_eng * post["engagement"])
            + (w_rec * post["recency"])
        )
        post["score"] = score
    return sorted(posts, key=lambda post: post["score"], reverse=True)


def fetch_stackexchange(topic):
    url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={topic}&site=stackoverflow"
    response = requests.get(url)
    data = response.json()
    items = data["items"]
    results = []
    for item in items:
        results.append(
            {
                "title": item["title"],
                "url": item["link"],
                "points": item["score"],
                "num_comments": item["answer_count"],
                "created_at_i": item["creation_date"],
            }
        )
    return results
