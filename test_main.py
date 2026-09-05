from main import score_posts
import time

now=time.time()

def make_post(title="python is great", points=100, num_comments=50, created_at_i=None):
    if created_at_i is None:
        created_at_i=now
    return{
        "title": title,
        "points": points,
        "num_comments": num_comments,
        "created_at_i": created_at_i,
    }
def test_relevamnt_post_ranks_first():
    posts=[make_post(title="cooking pasta"), make_post(title="python is great")]
    result=score_posts(posts,"python")
    assert result[0]["title"]=="python is great"
    
def test_engagement_post_ranks():
    posts=[make_post(points=10, num_comments=5),make_post(points=100, num_comments=50)]
    result=score_posts(posts,"python")
    assert result[0]["points"]> result[1]["points"]

def test_recency_post_ranks_first():
    posts=[make_post(created_at_i= now -100000000),make_post(created_at_i=now)]
    result=score_posts(posts,"python")
    assert result[0]["created_at_i"] > result[1]["created_at_i"]

def test_empty_list():
    result=score_posts([],"python")
    assert result==[]
    
def test_null_title():
    posts = [make_post(title=None), make_post(title="python")]
    result= score_posts(posts,"python")
    assert len(result)==2
        