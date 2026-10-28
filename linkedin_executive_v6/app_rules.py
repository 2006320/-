import re
from pathlib import Path
S={x.strip().casefold() for x in Path(__file__).with_name('surnames.txt').read_text().split(',')}
US=re.compile(r'\b(?:United States|USA|U\.S\.|California|New York|Texas|Florida|Washington|Massachusetts|New Jersey|Illinois|Pennsylvania|Georgia|Virginia|Maryland|Ohio|Michigan|Colorado|Arizona|Oregon|Seattle|Boston|Chicago|Houston|Dallas|Austin|Atlanta|San Francisco|Los Angeles)\b',re.I)
SENIOR=re.compile(r'\b(?:CEO|CFO|COO|President|Chairman|Chairwoman|Chief Executive Officer|Vice President|SVP|EVP|Managing Director|General Manager|Founder|Partner|Board Member|Executive Director)\b',re.I)
IT=re.compile(r'\b(?:CIO|CTO|Chief Information Officer|Chief Technology Officer|IT Director|IT Manager|Information Technology|Software Engineer|Software Developer|Programmer|DevOps|Cybersecurity|Cloud Engineer|IT Consultant)\b',re.I)
Y=re.compile(r'(?<!\d)(?:18\d{2}|19\d{2}|20\d{2})(?!\d)')
GRAD=re.compile(r'\b(?:graduated|graduation|class of|bachelor|degree|MBA)\b',re.I)
WORK=re.compile(r'\b(?:started career|began career|joined|founded|co-founded|worked at|started working|since)\b',re.I)
def inspect(url,name,txt,cutoff,err,config=None):
 r={'姓名':name,'姓氏':'','链接':url,'美国证据':'','高管证据':'','毕业年份证据':'','工作年份证据':'','东南亚经历证据':'','状态':'不合格','原因':'','访问情况':err}
 parts=re.findall(r"[A-Za-z][A-Za-z'’-]*",name)
 surname=parts[-1].casefold() if len(parts)>1 else ''
 r['姓氏']=surname
 if surname not in S:r['原因']='缺少完整姓名或姓氏不在白名单';return r
 if not txt:r['原因']='没有可核实的公开或授权资料';return r
 u=US.search(txt);t=SENIOR.search(txt);it=IT.search(txt)
 if u:r['美国证据']=txt[max(0,u.start()-55):u.end()+55]
 if t:r['高管证据']=txt[max(0,t.start()-55):t.end()+55]
 for m in Y.finditer(txt):
  year=int(m.group())
  if year>cutoff or year<1850:continue
  ctx=txt[max(0,m.start()-90):m.end()+90]
  if GRAD.search(ctx):r['毕业年份证据']+=(ctx[:160]+' | ')
  if WORK.search(ctx):r['工作年份证据']+=(ctx[:160]+' | ')
 r['毕业年份证据']=r['毕业年份证据'][:600];r['工作年份证据']=r['工作年份证据'][:600]
 sea=re.search(r'\b(?:Singapore|Malaysia|Indonesia|Vietnam|Thailand|Philippines|Cambodia|Laos|Myanmar|Brunei)\b',txt,re.I)
 if sea:r['东南亚经历证据']=txt[max(0,sea.start()-45):sea.end()+45]
 reasons=[]
 if not u:reasons.append('美国地区不明确')
 if not t:reasons.append('没有高管职位证据')
 if it:reasons.append('包含 IT 职位关键词，需人工消歧')
 if not(r['毕业年份证据'] or r['工作年份证据']):reasons.append('没有截止年份以前的明确经历证据')
 if reasons:r['原因']='；'.join(reasons)
 else:r['状态']='待人工核验';r['原因']='页面级条件命中，仍须核对全部证据属于同一人'
 return r
