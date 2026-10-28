"""PostgreSQL-only persistent storage. DATABASE_URL required for all processes."""
import os,json,time


def connect():
    url=os.environ.get('DATABASE_URL')
    if not url: raise RuntimeError('DATABASE_URL 未设置：必须连接共享 PostgreSQL 数据库')
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)

def init():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS templates(id BIGSERIAL PRIMARY KEY,name TEXT UNIQUE NOT NULL,config TEXT NOT NULL,created DOUBLE PRECISION NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS tasks(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,template_id BIGINT,config TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',created DOUBLE PRECISION NOT NULL,updated DOUBLE PRECISION NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS items(id BIGSERIAL PRIMARY KEY,task_id BIGINT NOT NULL REFERENCES tasks(id),url TEXT NOT NULL,name TEXT NOT NULL DEFAULT '',body TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'queued',result TEXT,attempts INTEGER NOT NULL DEFAULT 0,updated DOUBLE PRECISION NOT NULL,claimed_at DOUBLE PRECISION,UNIQUE(task_id,url))''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_items_queue ON items(status,task_id)')
        c.execute('''CREATE TABLE IF NOT EXISTS events(id BIGSERIAL PRIMARY KEY,task_id BIGINT NOT NULL,at DOUBLE PRECISION NOT NULL,message TEXT NOT NULL)''')

def event(c,task_id,message): c.execute('INSERT INTO events(task_id,at,message) VALUES(%s,%s,%s)',(task_id,time.time(),message))
def create_task(name,rows,config,template_id=None):
    now=time.time()
    with connect() as c:
        tid=c.execute('INSERT INTO tasks(name,template_id,config,status,created,updated) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id',(name,template_id,json.dumps(config,ensure_ascii=False),'queued',now,now)).fetchone()['id']
        for r in rows:c.execute('INSERT INTO items(task_id,url,name,body,updated) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(task_id,url) DO NOTHING',(tid,r['url'],r.get('name',''),r.get('text',''),now))
        event(c,tid,'任务创建')
    return tid

def set_status(tid,status):
    assert status in ('paused','queued','cancelled')
    with connect() as c:
        old=c.execute('SELECT status FROM tasks WHERE id=%s FOR UPDATE',(tid,)).fetchone()
        if not old or old['status'] in ('completed','cancelled'):return
        c.execute('UPDATE tasks SET status=%s,updated=%s WHERE id=%s',(status,time.time(),tid));event(c,tid,'状态切换：'+status)

def save_template(name,config):
    with connect() as c:c.execute('INSERT INTO templates(name,config,created) VALUES(%s,%s,%s) ON CONFLICT(name) DO UPDATE SET config=EXCLUDED.config',(name,json.dumps(config,ensure_ascii=False),time.time()))

def claim():
    with connect() as c:
        row=c.execute('''SELECT i.* FROM items i JOIN tasks t ON t.id=i.task_id WHERE t.status IN ('queued','running') AND i.status='queued' ORDER BY t.created,i.id FOR UPDATE OF i SKIP LOCKED LIMIT 1''').fetchone()
        if not row:return None
        now=time.time()
        c.execute("UPDATE items SET status='running',attempts=attempts+1,updated=%s,claimed_at=%s WHERE id=%s",(now,now,row['id']))
        c.execute("UPDATE tasks SET status='running',updated=%s WHERE id=%s AND status='queued'",(now,row['task_id']))
        return row

def finish(item_id,result):
    with connect() as c:
        row=c.execute('SELECT task_id FROM items WHERE id=%s FOR UPDATE',(item_id,)).fetchone()
        if not row:return
        tid=row['task_id'];now=time.time()
        c.execute("UPDATE items SET status='done',result=%s,updated=%s,claimed_at=NULL WHERE id=%s",(json.dumps(result,ensure_ascii=False),now,item_id))
        remaining=c.execute("SELECT COUNT(*) AS n FROM items WHERE task_id=%s AND status!='done'",(tid,)).fetchone()['n']
        if remaining==0:
            changed=c.execute("UPDATE tasks SET status='completed',updated=%s WHERE id=%s AND status IN ('queued','running') RETURNING id",(now,tid)).fetchone()
            if changed:event(c,tid,'全部完成')

def recover_stale(seconds=600):
    with connect() as c:
        c.execute("UPDATE items SET status='queued',claimed_at=NULL WHERE status='running' AND claimed_at<%s",(time.time()-seconds,))
        c.execute("UPDATE tasks SET status='queued' WHERE status='running' AND NOT EXISTS(SELECT 1 FROM items WHERE task_id=tasks.id AND status='running') AND EXISTS(SELECT 1 FROM items WHERE task_id=tasks.id AND status='queued')")

def list_tasks():
    with connect() as c:return c.execute('''SELECT t.id,t.name,t.status,t.created,t.updated,count(i.id) total,count(i.id) FILTER (WHERE i.status='done') done FROM tasks t LEFT JOIN items i ON i.task_id=t.id GROUP BY t.id ORDER BY t.id DESC''').fetchall()
def results(tid):
    with connect() as c:return c.execute('SELECT * FROM items WHERE task_id=%s ORDER BY id',(tid,)).fetchall()
def templates():
    with connect() as c:return c.execute('SELECT * FROM templates ORDER BY name').fetchall()
