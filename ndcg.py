import json
import math as m


with open("data.json","r") as f:
    data=json.load(f)
ndcg_all=[]
for entry in data:
    topic=entry["topic"]
    if entry['results'][0].get('judge') is None:
        continue
    grades=[r["judge"] for r in entry["results"]]
    dcg=0
    for i,  grade in enumerate(grades):
        dcg+= grade/m.log2(i+2)
    riyal_grades=sorted(grades,reverse=True)
    idcg=0
    for i,grade in enumerate(riyal_grades):
        idcg+=grade/m.log2(i+2)
    ndcg=0
    if idcg==0:
        ndcg=0
    else:    
        ndcg=dcg/idcg
    ndcg_all.append(ndcg)
    print(entry["topic"],ndcg)
        
average=sum(ndcg_all)/len(ndcg_all)
print(average)