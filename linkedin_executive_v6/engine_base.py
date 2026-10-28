import re, csv, io, ipaddress, socket
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
AGENT='LinkScopePublicResearch/1.0'
Y=re.compile(r'(?<!\d)(?:19\d{2}|20\d{2})(?!\d)')
WORK=re.compile(r'\b(started|joined|began|since|worked|working|employment|career|experience|employed)\b',re.I)
EDU=re.compile(r'\b(graduated|graduation|class of|earned degree|degree awarded)\b',re.I)
def parse_links(raw,data=None,name=''):
    urls=[x.strip() for x in raw.splitlines() if x.strip()]
    if data:
        txt=data.decode('utf-8-sig',errors='replace')
        if name.lower().endswith('.csv'):
            rows=list(csv.reader(io.StringIO(txt)))
            if rows:
                h=[x.lower().strip() for x in rows[0]]
                idx=next((h.index(x) for x in ('url','link','链接','网址') if x in h),0)
                urls.extend(r[idx].strip() for r in (rows[1:] if any(x in h for x in ('url','link','链接','网址')) else rows) if len(r)>idx and r[idx].strip())
        else:urls.extend(x.strip() for x in txt.splitlines() if x.strip())
    return list(dict.fromkeys(urls))
def linkedin(url):
    h=(urlsplit(url).hostname or '').lower()
    return h=='linkedin.com' or h.endswith('.linkedin.com')
def validate(url):
    p=urlsplit(url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password or p.port not in (None,80,443):raise ValueError('URL 格式/端口不支持')
    host=p.hostname.rstrip('.').lower()
    if host=='localhost' or host.endswith(('.local','.internal','.localhost')):raise ValueError('禁止访问内网')
    for x in socket.getaddrinfo(host,None,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(x[4][0]).is_global:raise ValueError('禁止访问非公网 IP')
    return p
def fetch(url):
    try:
        p=validate(url)
        if linkedin(url):return '', 'LinkedIn 不自动抓取；请上传授权资料'
        robots=f'{p.scheme}://{p.netloc}/robots.txt'
        r=requests.get(robots,headers={'User-Agent':AGENT},timeout=7,allow_redirects=False)
        if r.status_code==200:
            rp=RobotFileParser();rp.parse(r.text[:200000].splitlines())
            if not rp.can_fetch(AGENT,url):return '', 'robots.txt 禁止访问'
        elif r.status_code!=404:return '', '无法确认 robots.txt 许可'
        with requests.get(url,headers={'User-Agent':AGENT},timeout=12,allow_redirects=False,stream=True) as r:
            if r.status_code!=200:return '',f'HTTP {r.status_code}'
            if not any(t in r.headers.get('content-type','').lower() for t in ('text/html','text/plain')):return '', '非文本页面'
            chunks=bytearray()
            for c in r.iter_content(32768):
                chunks.extend(c)
                if len(chunks)>1000000:break
            txt=chunks.decode(r.encoding or 'utf-8',errors='replace')
        if '<html' in txt.lower():
            soup=BeautifulSoup(txt,'html.parser')
            for tag in soup(['script','style','nav','footer','header','noscript']):tag.decompose()
            txt=soup.get_text(' ',strip=True)
        return txt[:100000],''
    except (ValueError,OSError,requests.RequestException) as e:return '',str(e)[:160]
def assess(url,txt,rules,source,err=''):
    out={'链接':url,'来源':source,'抓取状态':'成功' if txt else err or '无资料','筛选结果':'待人工审核','工作年份':'','毕业年份':'','证据原文':'','证据来源':url,'原因':''}
    if not txt:out['原因']='无可核验资料';return out
    evidence=[];w=[];g=[]
    for m in Y.finditer(txt):
        year=int(m.group());near=txt[max(0,m.start()-90):m.end()+90]
        if WORK.search(near):w.append(year);evidence.append(near[:185])
        if EDU.search(near):g.append(year);evidence.append(near[:185])
    out['工作年份']=', '.join(map(str,sorted(set(w))[:20]));out['毕业年份']=', '.join(map(str,sorted(set(g))[:20]));out['证据原文']=' | '.join(evidence[:3])[:650]
    low=txt.casefold();must=[s.strip().casefold() for s in rules['must'] if s.strip()];exclude=[s.strip().casefold() for s in rules['exclude'] if s.strip()]
    if any(s in low for s in exclude):out['筛选结果']='不符合条件';out['原因']='出现排除词';return out
    if any(s not in low for s in must):out['筛选结果']='不符合条件';out['原因']='缺少必需词';return out
    a=any(y<=rules['work'] for y in w);b=any(y<=rules['grad'] for y in g)
    if (a and b if rules['mode']=='AND' else a or b):out['筛选结果']='符合条件（候选）';out['原因']='年份与附近语境匹配；须人工核实'
    else:out['原因']='缺少足够证据，不能认定不符合'
    return out
