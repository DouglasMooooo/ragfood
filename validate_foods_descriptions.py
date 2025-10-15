import json
from pathlib import Path
p=Path(r"c:\Users\Administrator\ragfood\ragfood_new\foods.json")
with p.open('r',encoding='utf-8') as f:
    data=json.load(f)
short=[]
for item in data:
    try:
        iid=int(item.get('id','0'))
    except:
        continue
    if iid>=91:
        desc=item.get('description','')
        wc=len(desc.split())
        if wc<75:
            short.append((iid,item.get('name',''),wc))
print('Total new items (>=91):', sum(1 for i in data if int(i['id'])>=91))
print('Descriptions under 75 words:', len(short))
for t in sorted(short):
    print(f"ID {t[0]:>3} | {t[2]:>3} words | {t[1]}")
