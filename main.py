from typing import Annotated
from fastapi import FastAPI,status,Depends,HTTPException,Request
import requests
import math as m
import time as t


app=FastAPI()


@app.get("/")
def homepage():
    return {"status":"ok"}

def fetch_hackernews(topic):
    url=f"http://hn.algolia.com/api/v1/search?query={topic}"
    response=requests.get(url)
    data=response.json()
    hits=data["hits"]
    results=[]
    for hit in hits:
        results.append({
            "title": hit["title"],
            "url":hit["url"],
            "points":hit["points"],
            "num_comments":hit["num_comments"],
            "created_at":hit["created_at"],
        })
    return results

@app.get("/search")
def search(topic:str):
    return fetch_hackernews(topic)

def score_posts(posts,topic):
    max_engagement=float('-inf')
    max_recency=float('-inf')
    for post in posts:
        engagement= m.log(1+post["points"]+post["num_comments"])
        age=t.time()- post["created_at_i"];
        recency=1/(age+1)
        title=post["title"] or ""#this is because some titles can be null                                             
        if topic.lower() in title.lower():
            relevance=1
        else: 
            relevance=0
        max_engagement=max(max_engagement,engagement)
        max_recency=max(max_recency,recency)
        post["engagement"]=engagement
        post["recency"]=recency
        post["relevance"]=relevance
    for post in posts:
        engagement=post["engagement"]/max_engagement
        recency=post["recency"]/max_recency
        score=relevance+engagement+recency
        post["score"]=score
    return sorted(posts,key=lambda post:post["score"],reverse=True)

