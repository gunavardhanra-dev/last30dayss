from dotenv import load_dotenv
from google import genai
import os
import json
import time
import logging


logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

load_dotenv()
with open("prompt1.txt","r",encoding="utf-8") as f:
     template=f.read()
with open("data.json","r",encoding="utf-8") as f:
     data=json.load(f)

client= genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
for entry in data:
     topic=entry["topic"]
     if entry["results"][0].get("judge") is not None:
          continue
     title_block="\n".join(
          f"{r['rank']}.{r['title']}" for r in entry["results"]
     )
     prompt= template.format(topic=topic, titles=title_block)
     try:
          interactions= client.interactions.create(
    
               model="gemini-3.8-flash",
               input=prompt,
          )    
     except Exception as e:
          logger.warning(f"API call failed for {topic}:{e}")
          continue
          
     try:
          grades =json.loads(interactions.output_text)
     except Exception as e:
          logger.warning(f"bad JSON for {topic}: {e} | raw: {interactions.output_text}")
          continue
     if len(grades)!=len(entry["results"]):#did Gemini give me the right number of grades?” before you touch any data
          logger.warning(f"grade count mismatch for {topic}:got{len(grades)},expected{len(entry)}")
          continue
     for grade, result in zip(grades,entry["results"]):
          result["judge"] = grade
     print(f"{topic}:{grades}") 
     time.sleep(6)
     with open("data.json",'w',encoding="utf-8") as json_file:
          json.dump(data,json_file,indent=4)
     