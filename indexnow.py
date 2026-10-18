# Сообщает Яндексу и Bing о новых и изменённых страницах (IndexNow).
# Запускается автоматически в GitHub после публикации сайта. Ошибки здесь сайт не ломают.
import json,os,re,subprocess,urllib.request
D=json.load(open("indexnow-urls.json",encoding="utf-8"))
home="https://"+D["host"]+"/"
try:
    changed=subprocess.run(["git","diff","--name-only","HEAD~1","HEAD"],capture_output=True,text=True,check=True).stdout.split("\n")
    changed=[c.strip().strip('"') for c in changed if c.strip()]
except Exception:
    changed=None
if changed is None or any(os.path.basename(c) in ("build.py","indexnow.py") for c in changed):
    urls=D["all"]; why="все страницы"
else:
    urls=set()
    for c in changed:
        if not c.lower().startswith("posts"): continue
        b=os.path.splitext(os.path.basename(c))[0].lower()
        b=re.sub(r"\s+","",b)
        for cand in (b,re.sub(r"-\d+$","",b)):
            if cand in D["byslug"]: urls.add(D["byslug"][cand])
    if urls: urls|={home,home+"obzory/",home+"mashiny/"}
    urls=sorted(u for u in urls if u in D["all"] or u in D["byslug"].values())
    why="новые и изменённые"
if not urls:
    print("IndexNow: новых страниц нет, ничего не отправляем"); raise SystemExit(0)
print(f"IndexNow: отправляем {len(urls)} адресов ({why})")
body=json.dumps({"host":D["host"],"key":D["key"],"keyLocation":f"https://{D['host']}/{D['key']}.txt","urlList":urls[:10000]}).encode()
for ep in ("https://yandex.com/indexnow","https://api.indexnow.org/indexnow"):
    try:
        r=urllib.request.urlopen(urllib.request.Request(ep,data=body,headers={"Content-Type":"application/json; charset=utf-8"}),timeout=30)
        print(ep,"→",r.status,"(принято)")
    except Exception as e:
        print(ep,"→ не удалось:",e)
