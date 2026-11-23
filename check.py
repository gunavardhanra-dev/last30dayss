import json
def count_check():
    with open('data.json','r') as f:
        data =json.load(f)
    judge_counter=0
    for entry in data:
        if entry['results'][0].get('judge') is not None:
            judge_counter+=1
    return judge_counter
print(count_check())