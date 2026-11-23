import requests
import json
import logging
import time



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open("test_topics.txt","r") as f:
    topics=[line.strip() for line in f if line.strip()]
all_data=[]
for topic in topics:
    api_url=f"http://localhost:8000/search?topic={topic}"
    response=requests.get(api_url)
    if response.status_code == 200:
        data= response.json()
        if not isinstance(data,list):
            logger.warning(f"no result:{topic}")
            time.sleep(7)
            continue
        top_data=data[:10]
        entry={
            "topic":topic,
            "results":[{"rank":i,"title":item["title"],"url":item["url"],"relevant":None}
            for i,item in enumerate(top_data,start=1)]
        }
        all_data.append(entry)
    else:
        logger.info(f"failed:{topic}")
    time.sleep(7)
with open("data.json", "w") as json_file:
    json.dump(all_data, json_file, indent=4)
    logger.info("appended data into json file complete")
