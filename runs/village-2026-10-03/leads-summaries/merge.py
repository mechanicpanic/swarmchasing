import json,glob,re
order=['M','A','B','C','D','E','F']
names=['Nervli','Nervensaegli','Adam','adam','george','George','Camila','Zak','Shoshannah','paleink','Laura','Katherine','Nadia','Runa Solberg','Evan Wang','Basil','aydi','Johnny Lin','FunnyMeadowlark','GrandPorpoise','Minuteandone','minutekiwi','Kira','Maggie Vale','Stewart Kahn Lundy','Carly','rigle','Muninn Alder','Elphick']
banned=['GPT-5.6 Terra','GPT-5.6 Luna','Terra','Luna']
out=[];flags=[]
for k in order:
    for f in sorted(glob.glob(f'parts/leads_{k}.jsonl')):
        for i,l in enumerate(open(f)):
            if not l.strip(): continue
            d=json.loads(l); s=json.dumps(d,ensure_ascii=False)
            for n in names:
                if re.search(r'(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])',s): flags.append((d['id'],n))
            for n in banned:
                if re.search(r'(?<![A-Za-z])'+re.escape(n)+r'(?![A-Za-z])',s): flags.append((d['id'],n))
            out.append(d)
print(len(out)); print(flags)
json.dump(out,open('/private/tmp/claude-501/-Users-phosphorus-projects/2142579d-8f2c-43d7-8b33-78b95f88771c/scratchpad/merged_preview.json','w'))
