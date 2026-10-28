import re,time,json
from urllib.parse import urlsplit,unquote
from storage import connect,event

def canonical(raw):
    s=str(raw).strip().strip('"\'<>[](),;')
    if not s:return ''
    if not re.match(r'^https?://',s,re.I):s='https://'+s
    try:p=urlsplit(s)
    except ValueError:return ''
    host=(p.hostname or '').lower()
    if host.startswith('www.'):host=host[4:]
    if host.startswith('m.'):host=host[2:]
    if host not in ('linkedin.com','linkedin.cn'):return ''
    path=unquote(p.path).replace('\\','/').strip('/')
    path=re.sub(r'/+','/',path)
    parts=path.split('/')
    if len(parts)<2 or parts[0].lower() not in ('in','pub'):return ''
    if parts[0].lower()=='in':
        if not parts[1]:return ''
        return 'https://www.linkedin.com/in/'+parts[1].lower()
    return 'https://www.linkedin.com/'+path.lower()

def init_dedup():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS dedup_pool(url TEXT PRIMARY KEY,first_source TEXT NOT NULL,added DOUBLE PRECISION NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS dedup_imports(id BIGSERIAL PRIMARY KEY,source TEXT,read_count INTEGER,inserted INTEGER,duplicates INTEGER,invalid INTEGER,created DOUBLE PRECISION)')
        c.execute('CREATE TABLE IF NOT EXISTS dedup_rejections(id BIGSERIAL PRIMARY KEY,task_id BIGINT,url TEXT,canonical_url TEXT,reason TEXT,created DOUBLE PRECISION)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_rejections_task ON dedup_rejections(task_id)')

def import_lines(lines,source='历史文件'):
    init_dedup();read=inserted=duplicates=invalid=0;now=time.time()
    # small transaction batches: avoid large long-lived locks and excessive RAM
    with connect() as c:
        for line in lines:
            line=line.strip()
            if not line:continue
            read+=1;url=canonical(line)
            if not url:invalid+=1;continue
            inserted_row=c.execute('INSERT INTO dedup_pool(url,first_source,added) VALUES(%s,%s,%s) ON CONFLICT(url) DO NOTHING RETURNING url',(url,source,now)).fetchone()
            if inserted_row:inserted+=1
            else:duplicates+=1
            if read%2000==0:c.commit()
        c.execute('INSERT INTO dedup_imports(source,read_count,inserted,duplicates,invalid,created) VALUES(%s,%s,%s,%s,%s,%s)',(source,read,inserted,duplicates,invalid,now))
    return dict(read=read,inserted=inserted,duplicates=duplicates,invalid=invalid)

def add_task_unique(name,rows,config,template_id=None):
    init_dedup();now=time.time();stats=dict(accepted=0,history_duplicates=0,batch_duplicates=0,invalid=0)
    with connect() as c:
        tid=c.execute('INSERT INTO tasks(name,template_id,config,status,created,updated) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id',(name,template_id,json.dumps(config,ensure_ascii=False),'queued',now,now)).fetchone()['id']
        seen=set()
        for r in rows:
            raw=str(r.get('url','')).strip();url=canonical(raw)
            if not url:stats['invalid']+=1;continue
            if url in seen:stats['batch_duplicates']+=1;continue
            seen.add(url)
            fresh=c.execute('INSERT INTO dedup_pool(url,first_source,added) VALUES(%s,%s,%s) ON CONFLICT(url) DO NOTHING RETURNING url',(url,'task:'+str(tid),now)).fetchone()
            if not fresh:
                stats['history_duplicates']+=1
                c.execute('INSERT INTO dedup_rejections(task_id,url,canonical_url,reason,created) VALUES(%s,%s,%s,%s,%s)',(tid,raw,url,'历史去重池已存在',now))
                continue
            c.execute('INSERT INTO items(task_id,url,name,body,updated) VALUES(%s,%s,%s,%s,%s)',(tid,url,str(r.get('name','')),str(r.get('text','')),now))
            stats['accepted']+=1
        if not stats['accepted']:c.execute("UPDATE tasks SET status='completed' WHERE id=%s",(tid,))
        event(c,tid,'全局去重完成：'+json.dumps(stats,ensure_ascii=False))
    return tid,stats

def pool_stats():
    init_dedup()
    with connect() as c:
        n=c.execute('SELECT COUNT(*) AS n FROM dedup_pool').fetchone()['n']
        imports=c.execute('SELECT * FROM dedup_imports ORDER BY id DESC LIMIT 20').fetchall()
    return n,imports
