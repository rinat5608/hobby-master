# Сборка сайта Hobby Master. Запускается автоматически в GitHub после каждого изменения.
# Новости лежат в папке posts: текстовый файл + фото с тем же именем. Настройки: settings.txt
import os,re,json,html,shutil,sys,glob
from datetime import datetime,timezone,date
from email.utils import format_datetime
from urllib.parse import quote,urlparse
from PIL import Image,ImageDraw,ImageFont
ROOT=os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
DOMAIN="https://hobby-master.online"; NAME="Hobby Master"
TAG="Новинки радиоуправляемых моделей: машины, катера, самолёты"
def readtxt(fp):
    b=open(fp,"rb").read()
    for enc in ("utf-8-sig","utf-16","cp1251"):
        try: return b.decode(enc).replace("\r\n","\n").replace("\r","\n")
        except Exception: pass
    return b.decode("utf-8","ignore")
def norm(s): return s.strip().lower().replace("ё","е")
SET={}
if os.path.exists("settings.txt"):
    for ln in readtxt("settings.txt").split("\n"):
        if ":" in ln and not ln.strip().startswith("#"):
            k,v=ln.split(":",1); SET[norm(k)]=v.strip()
TG=SET.get("телеграм",""); VK=SET.get("вконтакте",""); METRIKA_ID=re.sub(r"\D","",SET.get("метрика","")); MYTRACKER_ID=re.sub(r"\D","",SET.get("mytracker","") or SET.get("топ мейл","") or SET.get("top.mail.ru","")); YA_VERIFY=SET.get("яндекс вебмастер",""); G_VERIFY=SET.get("google","")
SECS={"mashiny":("Машины","машины"),"katera":("Катера и лодки","катера"),"samolety":("Самолёты","самолеты")}
SECMAP={"машины":"mashiny","машина":"mashiny","авто":"mashiny","катера":"katera","катер":"katera","лодки":"katera","лодка":"katera","катера и лодки":"katera","самолеты":"samolety","самолет":"samolety"}
MONTHS="января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()
TR={"а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"j","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"c","ч":"ch","ш":"sh","щ":"sch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"}
def slugify(s):
    s="".join(TR.get(c,c) for c in s.lower())
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")
def pdate(s):
    s=s.strip()
    m=re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$",s)
    if m: return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
    m=re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$",s)
    if m: return date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    m=re.match(r"^(\d{1,2})\s+([а-яё]+)\s+(\d{4})",s.lower())
    if m and m.group(2) in MONTHS: return date(int(m.group(3)),MONTHS.index(m.group(2))+1,int(m.group(1)))
    raise ValueError("не понял дату «"+s+"», нужен вид 06.10.2026")
BRANDS2=["Cross RC","Hobby Plus","Traction Hobby","Pro Boat","Team Associated","Element RC","Team Losi","RC4WD","Boom Racing","Carisma Scale","Killerbody RC","HPI Racing","Tekno RC","E-flite","Horizon Hobby"]
KINDMAP={"новость":"novost","новости":"novost","обзор":"obzor","сравнение":"sravnenie","топ":"top","подборка":"top","рейтинг":"top"}
KINDN={"novost":"Новость","obzor":"Обзор","sravnenie":"Сравнение","top":"Топ"}
SRCN={"bigsquidrc.com":"Big Squid RC","traxxas.com":"Traxxas","redcatracing.com":"Redcat","fmshobby.com":"FMS","ftx-rc.com":"FTX","remo-hobby.ru":"Remo Hobby"}
OUT="site"; shutil.rmtree(OUT,ignore_errors=True); os.makedirs(OUT+"/img"); os.makedirs(OUT+"/css")
e=html.escape
EMO=re.compile("[\U0001F300-\U0001FAFF☀-➿️\U0001F3FB-\U0001F3FF]")
A=[]; SKIP=[]; seen=set()
# Новости лежат в папке posts. Мак при распаковке иногда называет её «posts 2», «posts 3» — такие папки тоже читаются.
PDIRS=["posts"]+sorted(d for d in os.listdir(".") if os.path.isdir(d) and d.lower().startswith("posts") and d!="posts")
PFILES={}
for _d in PDIRS:
    for _f in os.listdir(_d): PFILES.setdefault(re.sub(r"\s+","",_f).lower(),os.path.join(_d,_f))  # без учёта регистра и пробелов
_TX={}
for _d in PDIRS:
    for _f in sorted(glob.glob(os.path.join(glob.escape(_d),"*.txt"))): _TX.setdefault(os.path.basename(_f).lower(),_f)
for fp in sorted(_TX.values(),key=lambda x:os.path.basename(x)):
    base=os.path.splitext(os.path.basename(fp))[0]
    if base.startswith("_") or norm(base).startswith(("шаблон","primer")): continue
    try:
        raw=readtxt(fp)
        m=re.search(r"^\s*-{3,}\s*$",raw,re.M)
        if not m: raise ValueError("нет строки --- между шапкой и текстом")
        H={}; SRCS=[]
        for ln in raw[:m.start()].split("\n"):
            if ":" in ln:
                k,v=ln.split(":",1); k=norm(k); v=v.strip()
                if k.startswith("источник"): SRCS+=re.findall(r"https?://[^\s,;]+",v)
                else: H[k]=v
        rest=EMO.sub("",raw[m.end():])
        rest="\n".join(l for l in rest.split("\n") if not l.strip().startswith("//"))
        specs=[]
        ms=re.search(r"^\s*характеристики\s*:\s*$",rest,re.M|re.I)
        if ms:
            specs=[re.sub(r"^\s*[-–—•*]\s*","",x).strip() for x in rest[ms.end():].split("\n") if x.strip()]
            rest=rest[:ms.start()]
        clean=lambda t:re.sub(r"\s+([.,!?])",r"\1",re.sub(r"\s+"," ",t)).strip()
        PHRE=re.compile(r"^\[\s*фото\s*(\d+)\s*\]",re.I)
        BL=[]
        for chunk in re.split(r"\n\s*\n",rest):
            lines=[l.strip() for l in chunk.split("\n") if l.strip()]
            if not lines: continue
            if all(PHRE.match(l) for l in lines):
                for l in lines: BL.append(("img",int(PHRE.match(l).group(1))))
            elif lines[0].startswith("#"):
                BL.append(("h",clean(lines[0].lstrip("#"))))
                if lines[1:]: BL.append(("p",clean(" ".join(lines[1:]))))
            elif all(l.startswith("|") for l in lines):
                rows=[[c.strip() for c in l.strip().strip("|").split("|")] for l in lines if not re.match(r"^\|[\s:|-]+\|?$",l)]
                if rows: BL.append(("table",rows))
            elif all(re.match(r"^[-–—•*]\s",l) for l in lines): BL.append(("ul",[clean(re.sub(r"^[-–—•*]\s*","",l)) for l in lines]))
            else: BL.append(("p",clean(" ".join(lines))))
        if not BL or BL[0][0]!="p": raise ValueError("первой строкой после --- должен идти заголовок")
        title=BL[0][1]; BL=BL[1:]
        kind=KINDMAP.get(norm(H.get("тип","новость")),"novost")
        name=H.get("название") or title
        d=pdate(H.get("дата","")) if H.get("дата") else date.today()
        sec=SECMAP.get(norm(H.get("раздел","машины")),"mashiny")
        scale=H.get("масштаб","").replace("/",":").replace(" ","")
        if scale and not re.match(r"^1:\d+$",scale): scale=""
        if "бренд" in H: brand=H["бренд"] if H["бренд"] not in ("-","—","нет","") else ""
        elif kind in ("sravnenie","top"): brand=""
        else: brand=next((b for b in BRANDS2 if norm(name).startswith(norm(b)+" ")),name.split()[0].rstrip(","))
        slug=slugify(base)
        if not slug or slug in seen: raise ValueError("имя файла должно быть уникальным и состоять из латинских букв, цифр и дефисов")
        def findph(stem):
            for x in ("jpg","jpeg","png","webp"):
                f=PFILES.get(f"{stem}.{x}".lower())
                if f: return f
        cov=findph(base+"-1") or findph(base)
        if not cov: raise ValueError(f"нет главного фото {base}-1.jpg")
        im=Image.open(cov).convert("RGB")
        big=im.copy(); big.thumbnail((1400,1400)); big.save(f"{OUT}/img/{slug}.jpg","JPEG",quality=84,progressive=True)
        PH={}
        for t_,v_ in BL:
            if t_=="img" and v_>1 and v_ not in PH:
                f2=findph(f"{base}-{v_}")
                if f2:
                    i2=Image.open(f2).convert("RGB"); i2.thumbnail((1400,1400)); i2.save(f"{OUT}/img/{slug}-{v_}.jpg","JPEG",quality=82,progressive=True); PH[v_]=i2.size
        BL=[x for x in BL if x[0]!="img" or x[1] in PH]
        body=[x[1] for x in BL if x[0] in ("p","h")]
        firstp=next((x[1] for x in BL if x[0]=="p"),title)
        desc=H.get("кратко") or firstp
        if len(desc)>220: desc=desc[:217].rsplit(" ",1)[0]+"…"
        seen.add(slug)
        src=SRCS[0] if SRCS else ""; host=urlparse(src).netloc.replace("www.","") if src else ""
        order=int(H["порядок"]) if H.get("порядок","").isdigit() else 0
        A.append(dict(slug=slug,sec=sec,kind=kind,order=order,date=f"{d.day} {MONTHS[d.month-1]} {d.year}",iso=d.isoformat(),name=name,scale=scale,status=H.get("статус",""),price=H.get("цена",""),src=src,srcs=SRCS,srcn=SRCN.get(host,host),credit=H.get("фото","производитель"),desc=desc,specs=specs,title=title,body=body,blocks=BL,ph=PH,w=big.size[0],h=big.size[1],brand=brand,bslug=slugify(brand) if brand else "",sslug=("masshtab-"+scale.replace(":","-")) if scale and sec=="mashiny" else ""))
    except Exception as ex:
        SKIP.append(f"{os.path.basename(fp)}: {ex}"); print("ПРОПУЩЕНО:",SKIP[-1])
if not A: sys.exit("Нет ни одной новости в папке posts")
A.sort(key=lambda a:(a['iso'],-a['order'],a['slug']),reverse=True)
BR=dict(sorted({a['bslug']:a['brand'] for a in A if a['bslug']}.items()))
REV=[a for a in A if a['kind']!='novost']
den=lambda a:int(a['scale'].split(':')[1])
SCL={a['sslug']:a['scale'] for a in sorted([a for a in A if a['sslug']],key=den)}
def plur(n,a="модель",b="модели",c="моделей"):
    return a if n%10==1 and n%100!=11 else (b if 2<=n%10<=4 and not 12<=n%100<=14 else c)
YEAR=date.today().year
CSS='''
:root{--bg:#fff;--ink:#111214;--mut:#6b6f76;--line:#ebecee;--line2:#e6e7e9;--soft:#f5f5f6;--yel:#ffd60a;--pill:#111214;--hdr:rgba(255,255,255,.92);color-scheme:light}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1012;--ink:#f1f1f2;--mut:#9a9ea6;--line:#26282d;--line2:#2c2f35;--soft:#1a1c20;--pill:#202228;--hdr:rgba(15,16,18,.9);color-scheme:dark}}
:root[data-theme=dark]{--bg:#0f1012;--ink:#f1f1f2;--mut:#9a9ea6;--line:#26282d;--line2:#2c2f35;--soft:#1a1c20;--pill:#202228;--hdr:rgba(15,16,18,.9);color-scheme:dark}
html{-webkit-text-size-adjust:100%}*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:18px/1.6 Inter,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit}img{max-width:100%;height:auto;display:block}
.wrap{max-width:760px;margin:0 auto;padding:0 20px}
header.top{position:sticky;top:0;z-index:5;background:var(--hdr);backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid var(--line)}
header.top .wrap{max-width:1080px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:16px;height:68px}
.brand{display:inline-flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink)}.ico{display:inline-flex;align-items:center;gap:8px}.ico svg{display:block}
.side{display:flex;justify-content:flex-end}.side a{text-decoration:none;font-size:15px;font-weight:550;color:var(--mut)}
@font-face{font-family:HMLogo;src:url(data:font/woff;base64,d09GRgABAAAAAAWgAAwAAAAABfgABAEGAAAAAAAAAAAAAAAAAAAAAAAAAABHUE9TAAAFUAAAACAAAAAgRHZMdUdTVUIAAAVwAAAALgAAADAfSCdrT1MvMgAAAZQAAABKAAAAYFqrYERjbWFwAAACEAAAAFMAAABsAZIBi2dseWYAAAKAAAAChgAAAvJhKwgCaGVhZAAAARwAAAA2AAAANiIKSlZoaGVhAAABVAAAAB4AAAAkB9kCRWhtdHgAAAHgAAAAMAAAADAdvQGwbG9jYQAAAmQAAAAaAAAAGgTvBCNtYXhwAAABdAAAACAAAAAgAH4ASm5hbWUAAAUIAAAAMgAAADQCLAqfcG9zdAAABTwAAAATAAAAIP+4ADIAAQAAAAQBBjbCaixfDzz1AAMD6AAAAADYpKnIAAAAAObxW+MAAP/5A1kCyAABAAcAAgAAAAAAAHicY2BkYGCR+reIIYV5GgMQMEcyMDKgAh4AVH8DJgAAAAEAAAAMACsABQAAAAAAAQACAB4ABgAAAGQAAAAAAAB4nGNgYc5k2sPAysDA1MUUwcDA4A2hGeMYjBj9gHwGDgY4YGRAAp4hbv4MCxgUGCJZpP4tYkhhyWcqhqlh0mM6CKQUGFgA8gUKoQAAAfQAAADUAAAC4QAQApMAPgIdAD4C2wA+A5YAPgMSACECjAA+AmcAKgJPABgCnwAHeJxjYGBgYmBgYAZiESDJCKZZGCKAtBCDAFCEiUGBwYnBlcGDwZfBnyGEIfL/f6CcAoMjXCwIJPb/4f+D//f/3/t/5/8d/7f93wQ2CQ0AAH48Fw4AAAAAJgAmAEAAcwCJAKIAvgDqARMBUQFjAXkAAHicNVJLaBNBGP7/2TZrH9TG7W6kgnEzya5dbYrZJoXQxgdRUJBKbaq1qbUJIVAhKVIPavEgBW2RIp6Kjx4kEcyKF1FoKTkoStGbiAcvnipVFJEWRaETZ7N1DvNg/u//HjNQC3zgOlkCAVxQB42wFcCtulVUPUKXjm5R0kVcZ41YYI9Ly6US3irdLJXI0kaczFTY+0qFEWTVDRBoBiDvSBlEqAcIqCKVTIk2EFxjf42n7DV7NnBqYHKSlDcOISCHAWeNcUyOY5rAA7u4GEVucVEuIGRvRN0MRcKdGqXbnEU2if/YlRxbwO7zlw5G2LjR3m6MP+rYt2fyKg6N9JzOknKqP9bXHA34/RpL6IGAcRfQZsFvnKUBQJJNmcqqzDnkLysrKLA+fELCs1N3pkl52qkl804tuikPg7pNPpN5i/2yLKyv6lfZJ1Jm31ECByEMckSjgxCoYGMkSRi07s/MW29evaxiimwIH7IzHNeKnzkJqJU/5CdZ5pnvAKjRtHBnJGKGFNu5i0aqjn0uuUUxUS+OjhbT6eLIuUK6P5PpT2QyCTFZzGYLyWQhmy0m740nh/O5s8N5u6/tILOZKagCtV04bUUJ/yeKhdttFnpPXoz2Hn/ApsY6+BjDOvablKOZ2JGch33Fa0Fjd9B2aHCl3VypwR9I03RTUZw2mh4kXDUX7aHaplrPTlI18OPyUfK8JhjQ9lKzIz4Qm70wMVu7QIJ+r3YgHk/EeiZ6xVDqsN5Gva0+pUk2+g6l8vm0T1e9Pk3xGCf2d6einHs7d9NV/VWAsu2FhknXorXIX2vjLQlP2/r4HZnjNVv4QZBpWODpk7k1a+3Fjes8b2N1FT+wj6jBPwAlyPwAAHicY2BgYGKQY2BmYGThZGBk4GNggLKZGDiAvACGfIYCIMxkyGMoZnAC8nIYUgA/1wTUAAB4nGNgZgCD/1sZjBiwAAAswgHqAAABAAAACgAcAB4AAURGTFQACAAEAAAAAP//AAAAAAAAeJxjYGRgYOBi0GHQY2B2cfMJYRBJSS0zYpADkokMcgwsQFmG//8Z4AAApTwG9gAA) format('woff');font-weight:700;font-display:swap}
.logo{background:var(--pill);color:var(--yel);font-family:HMLogo,Poppins,system-ui,sans-serif;font-weight:700;font-size:16px;letter-spacing:.06em;text-transform:uppercase;line-height:1.3;text-decoration:none;padding:7px 14px;border-radius:999px;white-space:nowrap}
nav{display:flex;gap:22px}nav a{text-decoration:none;font-size:15px;font-weight:550;color:var(--mut)}nav a:hover{color:var(--ink)}
.intro{padding:56px 0 8px}.intro h1{font-size:clamp(32px,6vw,52px);line-height:1.05;letter-spacing:-.035em;font-weight:800;margin:0 0 14px;text-wrap:balance}
.intro p{color:var(--mut);margin:0;font-size:19px;max-width:54ch}
.today{margin:28px 0 0;padding:14px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);display:flex;gap:6px 14px;flex-wrap:wrap;align-items:baseline;font-size:14.5px;line-height:1.5}
.today h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0;color:var(--mut);font-weight:700}
.today a{text-decoration:none;color:var(--mut)}.today a:hover{color:var(--ink);text-decoration:underline}
.feed{margin-top:8px}
.item{display:block;text-decoration:none;padding:36px 0;border-bottom:1px solid var(--line)}.item:last-child{border-bottom:0}
.item .im{border-radius:20px;overflow:hidden;background:var(--soft)}.item img{width:100%;aspect-ratio:16/9;object-fit:cover;transition:transform .5s cubic-bezier(.2,.7,.2,1)}
.item:hover img{transform:scale(1.025)}
.tags{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:14px;color:var(--mut);margin:18px 0 8px}
.tag{background:var(--yel);color:#111214;font-weight:700;font-size:12.5px;padding:3px 10px;border-radius:999px}
.item h2{font-size:clamp(23px,3.6vw,30px);line-height:1.18;letter-spacing:-.022em;font-weight:750;margin:0 0 8px;text-wrap:balance}
.item p{margin:0;color:var(--mut);font-size:17px;line-height:1.5}
h2.sec{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:48px 0 0;font-weight:700}
.crumbs{font-size:14px;color:var(--mut);padding:28px 0 0}.crumbs a{text-decoration:none}.crumbs a:hover{text-decoration:underline}
article.post{padding:6px 0 24px}
article.post h1{font-size:clamp(30px,5.4vw,46px);line-height:1.08;letter-spacing:-.032em;font-weight:800;margin:6px 0 14px;text-wrap:balance}
.meta{font-size:14.5px;color:var(--mut)}
.kick{display:inline-block;color:#111214;text-decoration:none;margin-right:6px;background:var(--yel);font-weight:700;font-size:12.5px;padding:3px 10px;border-radius:999px;margin-top:14px}
article.post figure{margin:26px -20px}article.post figure img{width:100%;border-radius:20px;background:var(--soft)}
figcaption{font-size:13px;color:var(--mut);margin:8px 20px 0}
@media(min-width:900px) and (max-width:1099px){article.post figure{margin:30px -80px}figcaption{margin-left:80px}}
.sform{display:flex;align-items:center;gap:8px;background:var(--soft);border-radius:12px;padding:0 12px;margin:14px 0 0}.sform svg{flex:none;color:var(--mut)}
.sform input{flex:1;min-width:0;border:0;background:none;font:inherit;font-size:16px;padding:11px 0;color:var(--ink);outline:none}.sform:focus-within{box-shadow:0 0 0 2px var(--ink)}
.sbtn{width:44px;height:44px;border-radius:12px;display:grid;place-content:center;color:var(--ink);margin-right:-10px}.sbtn:hover{background:var(--soft)}
.sres{margin-top:8px}.sres .cnt{color:var(--mut);font-size:15px;margin:18px 0 0}.bigsearch{margin-top:22px}.bigsearch input{font-size:18px;padding:14px 0}
mark{background:var(--yel);color:#111214;border-radius:3px;padding:0 2px}
@media(min-width:1100px){
.burger,nav.menu .x,.shade{display:none!important}
nav.menu{visibility:visible;transform:none;box-shadow:none!important;top:69px;left:max(20px,calc(50% - 520px));width:190px;padding:26px 0 30px;background:none;z-index:1;transition:none}
nav.menu p{margin:22px 0 4px;font-size:11.5px}nav.menu p:first-of-type{margin-top:22px}
nav.menu a{font-size:17px;font-weight:650;letter-spacing:-.01em;padding:4px 0}nav.menu a.s{font-size:15px;font-weight:500;color:var(--mut);padding:3px 0}nav.menu a.s:hover{color:var(--ink)}
nav.menu a.on{text-decoration:underline;text-decoration-color:var(--yel);text-decoration-thickness:3px;text-underline-offset:4px}
.sform{margin:0}.sform input{font-size:15px;padding:9px 0}
main.wrap{margin-left:max(250px,calc(50% - 290px));margin-right:auto}
header.top .wrap{grid-template-columns:1fr auto 1fr}.brand{grid-column:2}.side{grid-column:3}.sbtn{display:none}
}
article.post p{margin:0 0 18px}article.post p.first{font-size:21px;line-height:1.5;letter-spacing:-.005em}
article.post h2{font-size:24px;letter-spacing:-.02em;margin:40px 0 12px;font-weight:750}
table.spec{width:100%;border-collapse:collapse;font-size:16.5px;background:var(--soft);border-radius:16px;overflow:hidden}
table.spec th,table.spec td{text-align:left;padding:12px 18px;border-top:1px solid var(--line2);vertical-align:top}table.spec tr:first-child th,table.spec tr:first-child td{border-top:0}
table.spec th{width:38%;color:var(--mut);font-weight:500}table.spec td{font-weight:600}
ul.feat{list-style:none;padding:0;margin:0}ul.feat li{padding:10px 0 10px 26px;border-top:1px solid var(--line);position:relative;font-size:17px}ul.feat li:first-child{border-top:0}
ul.feat li:before{content:"";position:absolute;left:2px;top:19px;width:10px;height:10px;border-radius:50%;background:var(--yel)}
.src{font-size:14px;color:var(--mut);margin-top:32px!important}.src a{text-decoration:underline}
.tg{display:flex;justify-content:space-between;gap:12px;background:var(--pill);color:#fff;border-radius:16px;padding:18px 22px;margin:32px 0 0;text-decoration:none;font-weight:650}.tg b{color:var(--yel)}
footer{border-top:1px solid var(--line);margin-top:56px;padding:28px 0 44px;font-size:14px;color:var(--mut)}footer .wrap{max-width:1080px}
.burger{width:44px;height:44px;border:0;background:none;border-radius:12px;cursor:pointer;display:grid;place-content:center;gap:5px;justify-self:start;margin-left:-10px}.burger:hover{background:var(--soft)}.burger i{display:block;width:22px;height:2.4px;border-radius:2px;background:var(--ink)}
.shade{position:fixed;inset:0;background:rgba(17,18,20,.35);z-index:9}
.menu{position:fixed;top:0;left:0;bottom:0;width:min(330px,86vw);background:var(--bg);z-index:10;padding:22px 26px 30px;overflow:auto;transform:translateX(-102%);transition:transform .28s cubic-bezier(.2,.7,.2,1);display:flex;flex-direction:column;visibility:hidden}
.menu.open{transform:none;visibility:visible;box-shadow:0 0 60px rgba(0,0,0,.18)}
.menu p{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:700;margin:26px 0 6px}
.menu{gap:0}.menu a{color:var(--ink);text-decoration:none;font-size:24px;font-weight:750;letter-spacing:-.02em;padding:6px 0}.menu a.s{font-size:17px;font-weight:550;letter-spacing:0;padding:5px 0}
.menu a:hover{text-decoration:underline;text-decoration-color:var(--yel);text-decoration-thickness:3px;text-underline-offset:4px}
.menu .x{align-self:flex-end;width:40px;height:40px;border:0;background:var(--soft);border-radius:50%;font-size:24px;line-height:1;cursor:pointer;margin:-4px -8px 0 0}
.ico circle[fill="#fff"]{fill:var(--bg)}.menu .x{color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}.menu .chips a{font-size:13.5px!important;font-weight:600!important;letter-spacing:0;background:var(--soft);padding:4px 10px!important;border-radius:999px;color:var(--ink)!important;text-decoration:none!important}.menu .chips a:hover{background:var(--yel);color:#111214!important}
.theme{margin-top:26px;align-self:flex-start;border:1px solid var(--line2);background:none;color:var(--ink);font:inherit;font-size:14.5px;font-weight:600;border-radius:999px;padding:8px 14px;cursor:pointer;display:inline-flex;gap:8px;align-items:center}.theme:hover{background:var(--soft)}
.share{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:32px 0 0}.share b{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:700;margin-right:6px}
.share a{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-size:15px;font-weight:600;background:var(--soft);padding:9px 16px;border-radius:999px}.share a:hover{background:var(--yel);color:#111214}.share svg{flex:none}
.inf{display:inline-block;vertical-align:middle;margin-left:10px}.inf img{display:inline;border-radius:4px}
.tag.k{background:var(--pill);color:#fff}.kick.k{background:var(--pill);color:#fff}
article.post h3{font-size:22px;line-height:1.25;margin:34px 0 10px;letter-spacing:-.015em;font-weight:750}
.tw{overflow-x:auto;margin:6px 0 22px}table.cmp{width:100%;border-collapse:collapse;font-size:16px;min-width:460px}table.cmp th,table.cmp td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line2);vertical-align:top}table.cmp tr:first-child th{font-weight:700;border-bottom:2px solid var(--ink)}table.cmp td:first-child{color:var(--mut);font-weight:500}
article.post p.price{font-weight:700;background:var(--soft);border-radius:14px;padding:12px 16px}
.socials{background:var(--pill);color:#fff;border-radius:16px;padding:18px 22px;margin:32px 0 0}article.post .socials p{margin:0 0 12px;font-weight:600;font-size:17px}.socials a{display:inline-block;background:var(--yel);color:#111214;text-decoration:none;font-weight:700;font-size:15px;padding:8px 16px;border-radius:999px;margin:0 8px 6px 0}
.srcs{margin:6px 0 0;padding-left:18px}.srcs li{word-break:break-all}
.empty{background:var(--soft);border-radius:20px;padding:28px;margin-top:28px;color:var(--mut)}
.blist{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}.blist a{text-decoration:none;font-size:14.5px;font-weight:600;background:var(--soft);padding:6px 14px;border-radius:999px}.blist a:hover{background:var(--yel);color:#111214}.blist b{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);font-weight:700;align-self:center;margin-right:4px}
@media(max-width:700px){header.top .wrap{height:60px;gap:8px}.side a:not(.sbtn){display:none}.sbtn{margin-right:-10px}header.top .wrap{grid-template-columns:44px auto 44px;justify-content:space-between}.logo{font-size:13.5px;padding:7px 12px}.ico svg{width:32px;height:22px}.brand{gap:9px}.ico{gap:6px}}
@media(max-width:560px){body{font-size:17px}nav{gap:16px}.item{padding:28px 0}.item .im,article.post figure img{border-radius:16px}.intro{padding-top:36px}}
'''
open(OUT+"/css/style.css","w").write(CSS)
def page(path,title,descr,body,depth,kw="",extra="",ogimg=None,ogtype="website",noindex=False):
    r="../"*depth
    url=DOMAIN+"/"+path
    ver=f'<meta name="yandex-verification" content="{YA_VERIFY}">\n' if YA_VERIFY else "<!-- yandex-verification: сюда добавится код подтверждения Вебмастера -->\n"
    met=(f'''<script>(function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window,document,"script","https://mc.yandex.ru/metrika/tag.js","ym");ym({METRIKA_ID},"init",{{clickmap:true,trackLinks:true,accurateTrackBounce:true}});</script>
<noscript><div><img src="https://mc.yandex.ru/watch/{METRIKA_ID}" style="position:absolute;left:-9999px" alt=""></div></noscript>''' if METRIKA_ID else "<!-- Яндекс Метрика: счётчик добавится сюда после получения номера -->")
    gver=f'<meta name="google-site-verification" content="{e(G_VERIFY)}">\n' if G_VERIFY else ""
    tg=f'<a href="{TG}" rel="noopener">Telegram</a>' if TG else ""
    inf=f'<a class="inf" href="https://metrika.yandex.ru/stat/?id={METRIKA_ID}&amp;from=informer" target="_blank" rel="nofollow noopener"><img src="https://informer.yandex.ru/informer/{METRIKA_ID}/3_1_FFFFFFFF_EFEFEFFF_0_pageviews" width="88" height="31" alt="Яндекс.Метрика" title="Яндекс.Метрика: просмотры, визиты и посетители" loading="lazy"></a>' if METRIKA_ID else '<!-- информер Метрики появится здесь после установки счётчика -->'
    ogimg=ogimg or "og/site.jpg"
    og=f'<meta property="og:image" content="{DOMAIN}/{ogimg}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">\n<meta name="twitter:image" content="{DOMAIN}/{ogimg}">\n'
    h=f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(descr)}">
{f'<meta name="keywords" content="{e(kw)}">' if kw else ''}
<link rel="canonical" href="{url}">{chr(10)+'<meta name="robots" content="noindex,follow">' if noindex else ""}
<meta property="og:type" content="{ogtype}"><meta property="og:site_name" content="{NAME}"><meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(descr)}"><meta property="og:url" content="{url}">
{og}<meta name="twitter:card" content="summary_large_image">
{ver}{gver}<link rel="alternate" type="application/rss+xml" title="{NAME}" href="{DOMAIN}/rss.xml">
<link rel="icon" href="{r}favicon.svg" type="image/svg+xml">
<script>try{{var t=localStorage.getItem("theme");if(t)document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script>
<link rel="stylesheet" href="{r}css/style.css">
{extra}</head><body>
<header class="top"><div class="wrap"><button class="burger" type="button" aria-label="Открыть меню" aria-expanded="false" aria-controls="menu"><i></i><i></i><i></i></button><a class="brand" href="{r or './'}" aria-label="Hobby Master, на главную"><span class="logo">Hobby Master</span><span class="ico" aria-hidden="true"><svg viewBox="0 0 52 36" width="40" height="28" fill="none" stroke="currentColor" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19v-6a2 2 0 0 1 2-2h9l4-7h13l5 7h9a2 2 0 0 1 2 2v6"/><path d="M19 11h18M22 19h8"/><circle cx="13" cy="25" r="7.5" fill="#fff"/><circle cx="39" cy="25" r="7.5" fill="#fff"/><circle cx="13" cy="25" r="1.7" fill="currentColor" stroke="none"/><circle cx="39" cy="25" r="1.7" fill="currentColor" stroke="none"/></svg><svg viewBox="0 0 52 36" width="40" height="28" fill="none" stroke="currentColor" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"><path d="M5 16h31l11-4-6 10H10z"/><path d="M15 16l3-7h10l4 7"/><path d="M3 30q3.8-4 7.6 0t7.6 0 7.6 0 7.6 0 7.6 0 7.6 0"/></svg></span></a><div class="side">{tg}<a class="sbtn" href="{r}poisk/" aria-label="Поиск по сайту"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg></a></div></div></header>
<div class="shade" hidden></div>
<nav class="menu" id="menu" aria-label="Разделы сайта"><button class="x" type="button" aria-label="Закрыть меню">×</button>
<form class="sform" action="{r}poisk/" method="get" role="search"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg><input type="search" name="q" placeholder="Поиск по сайту" aria-label="Поиск по сайту" autocomplete="off"></form>
<p>Разделы</p><a href="{r or './'}">Все новинки</a>{f'<a href="{r}obzory/">Обзоры и сравнения</a>' if REV else ''}<a href="{r}mashiny/">Машины</a><a href="{r}katera/">Катера и лодки</a><a href="{r}samolety/">Самолёты</a>
<p>Бренды</p>{''.join(f'<a class="s" href="{r}brendy/{k}/">{v}</a>' for k,v in BR.items())}
{('<p>Масштабы</p><div class="chips">'+''.join(f'<a href="{r}mashiny/{k}/">{v}</a>' for k,v in SCL.items())+'</div>') if SCL else ''}
<p>Сайт</p><a class="s" href="{r}o-sajte/">О сайте</a>{tg.replace('<a ','<a class="s" ') if tg else ''}{f'<a class="s" href="{VK}" rel="noopener">ВКонтакте</a>' if VK else ''}<button class="theme" type="button" aria-label="Переключить тему"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg><span>Тёмная тема</span></button></nav>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">© {YEAR} {NAME}. {TAG}. Фотографии принадлежат производителям и изданиям-источникам. <a href="{r}o-sajte/">О сайте</a> · <a href="{r}rss.xml">RSS</a>{inf}</div></footer>
{met}
{f'''<!-- Top.Mail.Ru / MyTracker counter -->
<script>var _tmr=window._tmr||(window._tmr=[]);_tmr.push({{id:"{MYTRACKER_ID}",type:"pageView",start:(new Date()).getTime()}});(function(d,w,id){{if(d.getElementById(id))return;var ts=d.createElement("script");ts.async=true;ts.id=id;ts.src="https://top-fwz1.mail.ru/js/code.js";var s=d.getElementsByTagName("script")[0];s.parentNode.insertBefore(ts,s)}})(document,window,"tmr-code");</script>
<noscript><div><img src="https://top-fwz1.mail.ru/counter?id={MYTRACKER_ID};js=na" style="position:absolute;left:-9999px" alt=""></div></noscript>''' if MYTRACKER_ID else ""}
<script>(function(){{var m=document.getElementById('menu'),b=document.querySelector('.burger'),s=document.querySelector('.shade');function t(o){{m.classList.toggle('open',o);s.hidden=!o;b.setAttribute('aria-expanded',o);document.documentElement.style.overflow=o?'hidden':''}}b.onclick=function(){{t(!m.classList.contains('open'))}};s.onclick=m.querySelector('.x').onclick=function(){{t(false)}};document.addEventListener('keydown',function(e){{if(e.key==='Escape')t(false)}});var h=document.documentElement,tb=document.querySelector('.theme'),mq=window.matchMedia('(prefers-color-scheme: dark)');function cur(){{return h.getAttribute('data-theme')||(mq.matches?'dark':'light')}}function lab(){{tb.querySelector('span').textContent=cur()==='dark'?'Светлая тема':'Тёмная тема'}}tb.onclick=function(){{var n=cur()==='dark'?'light':'dark';h.setAttribute('data-theme',n);try{{localStorage.setItem('theme',n)}}catch(e){{}}lab()}};lab()}})();</script>
</body></html>'''
    fp=os.path.join(OUT,path,"index.html") if not path.endswith(".html") else os.path.join(OUT,path)
    os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w",encoding="utf-8").write(h)
def card(a,r,lazy=True):
    sc=f"<span>{a['scale']}</span><span>·</span>" if a['scale'] else ""
    return f'''<a class="item" href="{r}{a['sec']}/{a['slug']}/"><div class="im"><img src="{r}img/{a['slug']}.jpg" alt="{e(a['name'])}{', масштаб '+a['scale'] if a['scale'] else ''}" width="{a['w']}" height="{a['h']}"{' loading="lazy"' if lazy else ''}></div><div class="tags">{f'<span class="tag k">{KINDN[a["kind"]]}</span>' if a['kind']!='novost' else ''}{f'<span class="tag">{e(a["brand"])}</span>' if a['brand'] else ''}{sc}<time datetime="{a['iso']}">{a['date']}</time></div><h2>{e(a['title'])}</h2><p>{e(a['desc'])}</p></a>'''
# index
order=A; top=A[:4]
SHORT=lambda n:re.sub(r' (RTR|ARTR|Kit|Brushed RTR|Extreme Crawler RTR|with Interior RTR|Monster Truck Brushed RTR)$','',n)
ib=f'''<section class="intro"><h1>Новинки радиоуправляемых моделей</h1><p>Машины, катера и самолёты: новинки, обзоры и сравнения. Что вышло, сколько стоит и что выбрать.</p></section>
<section class="today"><h2>Свежее</h2>{''.join(f'<a href="{a["sec"]}/{a["slug"]}/">{e(SHORT(a["name"]))}</a>' for a in top)}</section>
<div class="feed">{''.join(card(a,'',i>0) for i,a in enumerate(order))}</div>'''
ld=json.dumps({"@context":"https://schema.org","@type":"WebSite","name":NAME,"url":DOMAIN+"/","inLanguage":"ru","potentialAction":{"@type":"SearchAction","target":DOMAIN+"/poisk/?q={search_term_string}","query-input":"required name=search_term_string"}},ensure_ascii=False)
page("",f"{NAME}: новинки радиоуправляемых моделей, машин и краулеров","Свежие новинки радиоуправляемых машин: краулеры, трофи и скейл-модели Traxxas, FMS, Vanquish, Tamiya и других брендов. Фото, характеристики и цены.",ib,0,"радиоуправляемые машины, rc машины, rc краулер, трофи модели, новинки rc, радиоуправляемые модели",f'<script type="application/ld+json">{ld}</script>',"og/site.jpg")
# articles
def rblocks(a,pre):
    o=[]; first=True
    for t,v in a['blocks']:
        if t=="p":
            if re.match(r"^цен[аы]\s*:",v,re.I): o.append(f'<p class="price">{e(v)}</p>')
            else: o.append(f'<p{" class=first" if first else ""}>{e(v)}</p>'); first=False
        elif t=="h": o.append(f"<h3>{e(v)}</h3>")
        elif t=="ul": o.append('<ul class="feat">'+"".join(f"<li>{e(x)}</li>" for x in v)+"</ul>")
        elif t=="table":
            hd,*rw=v
            o.append('<div class="tw"><table class="cmp"><tr>'+"".join(f"<th>{e(c)}</th>" for c in hd)+"</tr>"+"".join("<tr>"+"".join(f"<td>{e(c)}</td>" for c in r)+"</tr>" for r in rw)+"</table></div>")
        elif t=="img":
            w,h=a['ph'][v]; o.append(f'<figure><img src="{pre}img/{a["slug"]}-{v}.jpg" alt="{e(a["name"])}, фото {v}" width="{w}" height="{h}" loading="lazy"></figure>')
    return "\n".join(o)
def social():
    if not (TG or VK): return ""
    return '<div class="socials"><p>Ещё больше обзоров и новинок радиоуправляемых моделей — в нашем Telegram-канале и группе ВКонтакте.</p>'+(f'<a href="{TG}" rel="noopener">Telegram</a>' if TG else "")+(f'<a href="{VK}" rel="noopener">ВКонтакте</a>' if VK else "")+'</div>'
for i,a in enumerate(A):
    news=a['kind']=='novost'
    rows=[(k,v) for k,v in [("Бренд",a['brand']),("Масштаб",a['scale']),("Статус",a['status']),("Дата новости" if news else "Дата публикации",a['date'])] if v]
    sn=SECS[a['sec']][0]; msc=f", радиоуправляемая модель в масштабе {a['scale']}" if a['scale'] else ", радиоуправляемая модель"
    kick1=f'<a class="kick k" href="../../obzory/">{KINDN[a["kind"]]}</a>' if not news else ""
    kickb=f'<a class="kick" href="../../brendy/{a["bslug"]}/">{e(a["brand"])}</a>' if a['bslug'] else ""
    kick2=f'<a class="kick" href="../{a["sslug"]}/">Масштаб {a["scale"]}</a>' if a['sslug'] else ""
    if len(a['srcs'])>1: srcl='Источники:<ul class="srcs">'+"".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(u)}</a></li>' for u in a['srcs'])+"</ul>"
    elif a['src']: srcl=f'Источник: <a href="{e(a["src"])}" rel="nofollow noopener" target="_blank">{e(a["srcn"] if news else a["src"])}</a>. '
    else: srcl=""
    note="Цены в рублях пересчитаны приблизительно и могут отличаться от цен в магазинах." if news else f"Цены указаны на {a['date']} и могут меняться."
    feat=(f"<h2>Характеристики {e(a['name'])}</h2><ul class=\"feat\">"+"".join(f"<li>{e(x)}</li>" for x in a['specs'])+"</ul>") if a['specs'] else ""
    same=[x for x in A if x is not a and (x['kind']=='novost')==news]
    others=(same+[x for x in A if x is not a and x not in same])[:3]
    pu=f"{DOMAIN}/{a['sec']}/{a['slug']}/"; qt=quote(a['title']); qu=quote(pu,safe="")
    share=f'''<div class="share"><b>Поделиться</b><a href="https://t.me/share/url?url={qu}&amp;text={qt}" target="_blank" rel="noopener nofollow"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.3 18.7 19.6c-.2 1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.3-5 9.100-8.200c.4-.4-.1-.5-.6-.2L6.200 13.300 1.400 11.800c-1-.3-1-1 .2-1.500L20.400 3c.9-.3 1.700.2 1.500 1.300z"/></svg>Telegram</a><a href="https://vk.com/share.php?url={qu}&amp;title={qt}" target="_blank" rel="noopener nofollow"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12.800 17.500C6.500 17.500 2.900 13.200 2.700 6h3.200c.1 5.300 2.400 7.500 4.300 8V6h3v4.500c1.800-.2 3.700-2.300 4.400-4.500h3c-.5 2.800-2.600 4.900-4 5.800 1.500.7 3.800 2.500 4.700 5.700h-3.300c-.7-2.200-2.500-3.900-4.800-4.200v4.200z"/></svg>ВКонтакте</a><a href="https://max.ru/:share?text={qt}%20{qu}" target="_blank" rel="noopener nofollow"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a9 9 0 0 0-7.700 13.700L3 21l4.500-1.200A9 9 0 1 0 12 3z"/></svg>MAX</a></div>'''
    crumb2=f'<a href="../">{sn}</a>' if news else '<a href="../../obzory/">Обзоры и сравнения</a>'
    crumb3=f' / <a href="../../brendy/{a["bslug"]}/">{e(a["brand"])}</a>' if a['bslug'] else ""
    meta=("" if news or a['name']==a['title'] else e(a['name'])+" · ")+f'<time datetime="{a["iso"]}">{a["date"]}</time>'
    spec=("<h2>Коротко о модели</h2><table class=\"spec\">"+"".join(f"<tr><th>{k}</th><td>{e(v)}</td></tr>" for k,v in rows)+"</table>") if a['kind'] in ('novost','obzor') else ""
    b=(f'<div class="crumbs"><a href="../../">Главная</a> / {crumb2}{crumb3}</div>\n'
       f'<article class="post">{kick1}{kickb}{kick2}<h1>{e(a["title"])}</h1><div class="meta">{meta}</div>\n'
       f'<figure><img src="../../img/{a["slug"]}.jpg" alt="{e(a["name"])}{msc}" width="{a["w"]}" height="{a["h"]}"><figcaption>{e(a["name"])}. Фото: {e(a["credit"])}</figcaption></figure>\n'
       f'{rblocks(a,"../../")}\n{spec}\n{feat}{share}{social()}\n<p class="src">{srcl}{note}</p></article>\n'
       f'<h2 class="sec">{"Ещё новинки" if news else "Ещё обзоры"}</h2><div class="feed">'+"".join(card(x,'../../') for x in others)+'</div>')
    descr=(a['desc']+" "+("Цена: "+a['price']+". " if a['price'] else "")+(f"Масштаб {a['scale']}, характеристики и фото." if a['scale'] else "Характеристики и фото."))[:300] if news else a['desc'][:300]
    ld=json.dumps({"@context":"https://schema.org","@type":"NewsArticle" if news else "Article","headline":a['title'][:110],"datePublished":a['iso'],"dateModified":a['iso'],"image":[f"{DOMAIN}/img/{a['slug']}.jpg"]+[f"{DOMAIN}/img/{a['slug']}-{n}.jpg" for n in sorted(a['ph'])],"author":{"@type":"Organization","name":NAME,"url":DOMAIN+"/"},"publisher":{"@type":"Organization","name":NAME},"mainEntityOfPage":pu,"inLanguage":"ru"},ensure_ascii=False)
    il=[{"@type":"ListItem","position":1,"name":"Главная","item":DOMAIN+"/"},{"@type":"ListItem","position":2,"name":sn if news else "Обзоры и сравнения","item":f"{DOMAIN}/{a['sec']}/" if news else f"{DOMAIN}/obzory/"}]
    if a['bslug']: il.append({"@type":"ListItem","position":3,"name":a['brand'],"item":f"{DOMAIN}/brendy/{a['bslug']}/"})
    il.append({"@type":"ListItem","position":len(il)+1,"name":a['name']})
    bc=json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":il},ensure_ascii=False)
    if news:
        kw=f"{a['name']}, {a['brand']}, "+({"mashiny":f"rc краулер {a['scale']}, радиоуправляемая машина","katera":"радиоуправляемый катер, rc лодка","samolety":"радиоуправляемый самолёт, rc самолёт"}[a['sec']])+", новинка, обзор, цена, характеристики"
        ttl=f"{a['name']}{' ('+a['scale']+')' if a['scale'] else ''}: обзор новинки, характеристики, цена | {NAME}"
    else:
        kw=", ".join(x for x in [a['name'],f"обзор {a['name']}" if a['kind']=='obzor' else "",a['brand'],f"краулер {a['scale']}" if a['scale'] else "","радиоуправляемый краулер","какой краулер купить","цена"] if x)
        ttl=(f"Обзор {a['name']}: плюсы, минусы, цена | {NAME}" if a['kind']=='obzor' else f"{a['title']} | {NAME}")
    page(f"{a['sec']}/{a['slug']}/",ttl,descr,b,2,kw,f'<script type="application/ld+json">{ld}</script>\n<script type="application/ld+json">{bc}</script>','og/'+a['slug']+'.jpg',"article")
if REV:
    page("obzory/",f"Обзоры и сравнения радиоуправляемых краулеров | {NAME}","Обзоры радиоуправляемых краулеров с плюсами и минусами, сравнения моделей и подборки по бюджету. Traxxas, Axial, Redcat, FMS, FTX и другие.",'<div class="crumbs"><a href="../">Главная</a> / Обзоры и сравнения</div><section class="intro" style="padding-top:18px"><h1>Обзоры и сравнения</h1><p>Честные обзоры моделей, сравнения и подборки: что выбрать и за что платить.</p></section><div class="feed">'+"".join(card(x,"../",k>0) for k,x in enumerate(REV))+'</div>',1,"обзоры радиоуправляемых машин, обзор краулера, сравнение краулеров, какой краулер купить, топ краулеров")
page("o-sajte/",f"О сайте | {NAME}","Hobby Master рассказывает о новинках радиоуправляемых моделей: краулеры, трофи и скейл-модели. Как мы отбираем новости и откуда берём данные.",f'''<article class="post"><h1>О сайте</h1><p>«{NAME}» рассказывает о новинках в мире радиоуправляемых моделей. Главные темы: краулеры, трофи и копийные внедорожники, а также радиоуправляемые катера.</p><p>Мы следим за анонсами производителей и профильных изданий и коротко пересказываем главное: что за модель, чем она интересна, какие у неё характеристики и сколько она стоит.</p><h2>Откуда данные</h2><p>Характеристики и цены взяты из официальных анонсов и новостей профильных изданий, ссылка на источник есть под каждой новостью. Цены в рублях пересчитаны приблизительно и могут отличаться от цен в магазинах.</p><h2>Фотографии</h2><p>Фотографии принадлежат производителям моделей и изданиям-источникам.</p></article>''',1)
IDX=json.dumps([{"u":f"{a['sec']}/{a['slug']}/","t":a['title'],"n":a['name'],"b":a['brand'] or KINDN[a['kind']],"s":a['scale'],"d":a['date'],"p":(a['price'] or "").split(",")[0],"i":f"img/{a['slug']}.jpg","x":" ".join([a['desc']]+a['body']+a['specs']+[a['status'],KINDN[a['kind']]]+[" ".join(" ".join(r) for r in b[1]) for b in a['blocks'] if b[0]=="table"])} for a in A],ensure_ascii=False).replace("</","<\\/")
SJS='''<script>(function(){var D=__IDX__,R="../";function nz(s){return (s||"").toLowerCase().replace(/ё/g,"е")}
function st(w){return /[а-я]/.test(w)&&w.length>4?w.slice(0,Math.max(4,w.length-2)):w}
function esc(s){return s.replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
var inp=document.getElementById("q"),out=document.getElementById("res");
function run(){var q=nz(inp.value).trim(),ws=q.split(/[^a-zа-я0-9:]+/).filter(Boolean).map(st);
if(!ws.length){out.innerHTML='<p class="cnt">Введите запрос: название модели, бренд или характеристику. Например, «Traxxas», «1:18» или «портальные мосты».</p>';return}
var r=D.map(function(a){var hi=nz(a.t+" "+a.n+" "+a.b+" "+a.s),lo=nz(a.x),sc=0;for(var i=0;i<ws.length;i++){if(hi.indexOf(ws[i])>=0)sc+=3;else if(lo.indexOf(ws[i])>=0)sc+=1;else return null}return{a:a,sc:sc}}).filter(Boolean).sort(function(x,y){return y.sc-x.sc});
var h='<p class="cnt">'+(r.length?"Найдено: "+r.length:"Ничего не найдено. Попробуйте другое слово или название бренда.")+'</p><div class="feed">';
r.forEach(function(o){var a=o.a;h+='<a class="item" href="'+R+a.u+'"><div class="im"><img loading="lazy" src="'+R+a.i+'" alt="'+esc(a.n)+'"></div><div class="tags"><span class="tag">'+esc(a.b)+'</span>'+(a.s?'<span>'+a.s+'</span><span>·</span>':'')+'<span>'+a.d+'</span></div><h2>'+esc(a.t)+'</h2></a>'});
out.innerHTML=h+'</div>';try{history.replaceState(null,"","?q="+encodeURIComponent(inp.value))}catch(e){}}
var m=/[?&]q=([^&]*)/.exec(location.search);if(m)inp.value=decodeURIComponent(m[1].replace(/\\+/g," "));
var t;inp.addEventListener("input",function(){clearTimeout(t);t=setTimeout(run,120)});document.getElementById("sf").addEventListener("submit",function(e){e.preventDefault();run()});run();if(!m)inp.focus()})();</script>'''.replace("__IDX__",IDX)
page("poisk/",f"Поиск по сайту | {NAME}","Поиск по новостям и моделям на сайте.",'''<section class="intro" style="padding-top:36px"><h1>Поиск</h1><form class="sform bigsearch" id="sf" role="search"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg><input id="q" type="search" name="q" placeholder="Модель, бренд или характеристика" aria-label="Поиск по сайту" autocomplete="off"></form></section><div class="sres" id="res"></div>'''+SJS,1,noindex=True)
page("404.html","Страница не найдена | "+NAME,"Такой страницы нет.",'<article class="post"><h1>Страница не найдена</h1><p><a href="/">Перейти к новинкам</a></p></article>',0)
byd=A; CARS=[a for a in A if a['sec']=='mashiny']
bl='<div class="blist"><b>Масштаб</b>'+''.join(f'<a href="{k}/">{v}</a>' for k,v in SCL.items())+'</div><div class="blist" style="margin-top:10px"><b>Бренд</b>'+''.join(f'<a href="../brendy/{k}/">{v}</a>' for k,v in BR.items())+'</div>'
for k,v in SCL.items():
    it=[a for a in byd if a['sslug']==k]
    oth=''.join(f'<a href="../{k2}/">{v2}</a>' for k2,v2 in SCL.items() if k2!=k)
    page(f"mashiny/{k}/",f"Радиоуправляемые машины {v}: новинки, краулеры и трофи | {NAME}",f"Радиоуправляемые машины в масштабе {v}: новинки краулеров, трофи и скейл-моделей с характеристиками, фото и ценами.",f'<div class="crumbs"><a href="../../">Главная</a> / <a href="../">Машины</a> / Масштаб {v}</div><section class="intro" style="padding-top:18px"><h1>Радиоуправляемые машины {v}</h1><p>Новинки в масштабе {v}: {len(it)} {plur(len(it))} в ленте.</p><div class="blist"><b>Другие масштабы</b>{oth}</div></section><div class="feed">{"".join(card(a,"../../",i>0) for i,a in enumerate(it))}</div>',2,f"радиоуправляемые машины {v}, rc {v}, краулер {v}, модели {v}, масштаб {v}",ogimg="og/site.jpg",noindex=len(it)<2)
if CARS:
    page("mashiny/",f"Радиоуправляемые машины: новинки, обзоры, цены | {NAME}","Новинки радиоуправляемых машин: краулеры, трофи и скейл-модели в разных масштабах. Характеристики, фото и цены на модели Traxxas, FMS, Vanquish, Tamiya.",f'<div class="crumbs"><a href="../">Главная</a> / Машины</div><section class="intro" style="padding-top:18px"><h1>Радиоуправляемые машины</h1><p>Краулеры, трофи и скейл-модели: все новинки с характеристиками и ценами.</p>{bl}</section><div class="feed">{"".join(card(a,"../",i>0) for i,a in enumerate(CARS))}</div>',1,"радиоуправляемые машины, rc машины, rc краулеры, трофи модели, скейл модели")
for k,v in BR.items():
    it=[a for a in byd if a['bslug']==k]
    page(f"brendy/{k}/",f"{v}: новинки радиоуправляемых моделей | {NAME}",f"Все новинки {v}: радиоуправляемые модели, краулеры и трофи. Характеристики, фото и цены.",f'<div class="crumbs"><a href="../../">Главная</a> / Бренды</div><section class="intro" style="padding-top:18px"><h1>{v}</h1><p>Новинки и обзоры {v}: {len(it)} {plur(len(it),"материал","материала","материалов")}.</p></section><div class="feed">{"".join(card(a,"../../",i>0) for i,a in enumerate(it))}</div>',2,f"{v}, {v} новинки, {v} rc, радиоуправляемые модели {v}",noindex=len(it)<2)
for p_,t_,d_,k_ in [("mashiny","Радиоуправляемые машины","Новинки радиоуправляемых машин: краулеры, трофи и скейл-модели.","радиоуправляемые машины, rc машины"),("katera","Радиоуправляемые катера и лодки","Новинки радиоуправляемых катеров и лодок: глиссеры, катамараны, джет-боты и копийные суда.","радиоуправляемые катера, rc лодки, радиоуправляемые лодки, rc катер"),("samolety","Радиоуправляемые самолёты","Новинки радиоуправляемых самолётов: тренеры, копии, планеры и модели для 3D-пилотажа.","радиоуправляемые самолёты, rc самолёты, авиамодели")]:
    it=[a for a in A if a['sec']==p_]
    if p_=="mashiny" and it: continue
    cr=f'<div class="crumbs"><a href="../">Главная</a> / {SECS[p_][0]}</div><section class="intro" style="padding-top:18px"><h1>{t_}</h1><p>{d_}</p></section>'
    if it: page(p_+"/",f"{t_}: новинки, обзоры, цены | {NAME}",d_+" Характеристики, фото и цены.",cr+f'<div class="feed">{"".join(card(a,"../",i>0) for i,a in enumerate(it))}</div>',1,k_)
    else: page(p_+"/",f"{t_}: новинки | {NAME}",d_,cr+'<div class="empty">Раздел готовится. Первые новости появятся здесь в ближайшее время, а пока посмотрите <a href="../">все новинки</a>.</div>',1,noindex=True)
open(OUT+"/favicon.svg","w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="18" fill="#111214"/><text x="32" y="43" font-family="Arial,sans-serif" font-weight="900" font-size="26" text-anchor="middle" fill="#ffd60a">HM</text></svg>')
open(OUT+"/robots.txt","w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
u=[("",A[0]['iso'])]+[(f"{a['sec']}/{a['slug']}/",a['iso']) for a in A]+[(k+"/",max(a['iso'] for a in A if a['sec']==k)) for k in SECS if any(a['sec']==k for a in A)]+[(f"brendy/{k}/",max(a['iso'] for a in A if a['bslug']==k)) for k in BR if sum(a['bslug']==k for a in A)>1]+[(f"mashiny/{k}/",max(a['iso'] for a in A if a['sslug']==k)) for k in SCL if sum(a['sslug']==k for a in A)>1]+([("obzory/",REV[0]['iso'])] if REV else [])+[("o-sajte/","2026-10-11")]
open(OUT+"/sitemap.xml","w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"".join(f"<url><loc>{DOMAIN}/{p}</loc><lastmod>{d}</lastmod></url>\n" for p,d in u)+"</urlset>\n")
def rfc(a): return format_datetime(datetime.fromisoformat(a['iso']).replace(hour=9,tzinfo=timezone.utc))
def cdata(a): return "<![CDATA["+f'<img src="{DOMAIN}/img/{a["slug"]}.jpg" alt="{e(a["name"])}">'+rblocks(a,DOMAIN+"/")+("<ul>"+"".join(f"<li>{e(x)}</li>" for x in a['specs'])+"</ul>" if a['specs'] else "")+"]]>"
items="".join(f"<item><title>{e(a['title'])}</title><link>{DOMAIN}/{a['sec']}/{a['slug']}/</link><guid isPermaLink=\"true\">{DOMAIN}/{a['sec']}/{a['slug']}/</guid><pubDate>{rfc(a)}</pubDate><category>{SECS[a['sec']][0]}</category>{f"<category>{e(a['brand'])}</category>" if a['brand'] else ""}{f"<category>{KINDN[a['kind']]}</category>" if a['kind']!='novost' else ""}<description>{e(a['desc'])}</description><content:encoded>{cdata(a)}</content:encoded><enclosure url=\"{DOMAIN}/img/{a['slug']}.jpg\" type=\"image/jpeg\" length=\"{os.path.getsize(OUT+'/img/'+a['slug']+'.jpg')}\"/></item>\n" for a in byd)
open(OUT+"/rss.xml","w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>{NAME}</title><link>{DOMAIN}/</link><atom:link href="{DOMAIN}/rss.xml" rel="self" type="application/rss+xml"/><description>{TAG}</description><language>ru</language><lastBuildDate>{rfc(byd[0])}</lastBuildDate><image><url>{DOMAIN}/og/site.jpg</url><title>{NAME}</title><link>{DOMAIN}/</link></image>\n{items}</channel></rss>\n')
open(OUT+"/CNAME","w").write("hobby-master.online\n")

# картинки-превью для ссылок (Telegram, ВК и т. д.)
os.makedirs(OUT+"/og",exist_ok=True)
def F(n,s): return ImageFont.truetype(os.path.join("fonts",n),s)
def spaced(dr,xy,t,f,fill,sp):
    x,y=xy
    for ch in t: dr.text((x,y),ch,font=f,fill=fill); x+=dr.textlength(ch,font=f)+sp
def swidth(dr,t,f,sp): return sum(dr.textlength(ch,font=f)+sp for ch in t)-sp
def pill(im,cx,cy,size,padx,pady,left=None):
    dr=ImageDraw.Draw(im); f=F("Poppins-Bold.ttf",size); sp=size*.06; t="HOBBY MASTER"
    w=swidth(dr,t,f,sp); asc,desc=f.getmetrics(); h=size*1.0
    W=w+2*padx; Hh=h+2*pady; x0=left if left is not None else cx-W/2; y0=cy-Hh/2
    dr.rounded_rectangle([x0,y0,x0+W,y0+Hh],radius=Hh/2,fill="#ffd60a")
    bb=f.getbbox("HM"); spaced(dr,(x0+padx,cy-(bb[1]+bb[3])/2),t,f,"#111214",sp)
    return x0+W
def wrap(dr,t,f,maxw):
    out=[]; cur=""
    for w in t.split():
        if dr.textlength((cur+" "+w).strip(),font=f)<=maxw: cur=(cur+" "+w).strip()
        else:
            if cur: out.append(cur)
            cur=w
    return out+[cur]
SS=2
def og(a):
    im=Image.new("RGB",(1200*SS,630*SS),"#fff")
    ph=Image.open(f"{OUT}/img/{a['slug']}.jpg"); k=min(1120*SS/ph.width,440*SS/ph.height); ph=ph.resize((int(ph.width*k),int(ph.height*k)),Image.LANCZOS)
    im.paste(ph,((1200*SS-ph.width)//2,(470*SS-ph.height)//2))
    dr=ImageDraw.Draw(im); dr.rectangle([0,470*SS,1200*SS,630*SS],fill="#111214")
    x=pill(im,0,550*SS,25*SS,22*SS,13*SS,left=48*SS)+30*SS
    maxw=1200*SS-48*SS-x; sub=" · ".join(x for x in [KINDN[a['kind']] if a['kind']!='novost' else "",a['brand'],f"масштаб {a['scale']}" if a['scale'] else ""] if x)
    for size in (38,34,30,27,24):
        f=F("Inter-ExtraBold.otf",size*SS); lines=wrap(dr,a['name'],f,maxw)
        if len(lines)<=2 and all(dr.textlength(l,font=f)<=maxw for l in lines): break
    lines=lines[:2]; fs=F("Inter-SemiBold.otf",21*SS); lh=size*1.14*SS
    tot=lh*len(lines)+8*SS+24*SS; y=550*SS-tot/2
    for l in lines: dr.text((x,y),l,font=f,fill="#fff"); y+=lh
    dr.text((x,y+6*SS),sub,font=fs,fill="#ffd60a")
    im.resize((1200,630),Image.LANCZOS).save(f"{OUT}/og/{a['slug']}.jpg","JPEG",quality=86)
for a in A: og(a)
im=Image.new("RGB",(1200*SS,630*SS),"#111214"); dr=ImageDraw.Draw(im)
pill(im,600*SS,235*SS,74*SS,56*SS,36*SS)
for t,fn,s,y,c in [("Новинки радиоуправляемых моделей","Inter-ExtraBold.otf",38,372,"#fff"),("Машины · Катера · Самолёты","Inter-SemiBold.otf",28,445,"#9a9ea6")]:
    f=F(fn,s*SS); dr.text((600*SS-dr.textlength(t,font=f)/2,y*SS),t,font=f,fill=c)
im.resize((1200,630),Image.LANCZOS).save(f"{OUT}/og/site.jpg","JPEG",quality=88)
print(f"Готово: новостей {len(A)}, файлов {sum(len(f) for _,_,f in os.walk(OUT))}")
if SKIP: print("Не попали на сайт:\n- "+"\n- ".join(SKIP))
