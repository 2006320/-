import time, argparse, json
from storage import init,claim,finish,recover_stale,connect
from engine_base import fetch
from app_rules import inspect

def loop(once=False):
 init();recover_stale()
 while True:
  item=claim()
  if not item:
   if once:break
   time.sleep(2);continue
  try:
   with connect() as c:config=json.loads(c.execute('SELECT config FROM tasks WHERE id=%s',(item['task_id'],)).fetchone()['config'])
   txt=item['body'];err='用户提供文本' if txt else ''
   if not txt:txt,err=fetch(item['url'])
   outcome=inspect(item['url'],item['name'],txt,int(config['cutoff']),err,config)
  except Exception as e:outcome={'状态':'不合格','原因':'处理异常：'+str(e)[:180],'链接':item['url'],'姓名':item['name']}
  finish(item['id'],outcome)
  if once:break
  time.sleep(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');loop(p.parse_args().once)
