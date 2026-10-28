import io,json,time
from pathlib import Path
import pandas as pd
import streamlit as st
from engine_base import parse_links
from storage import init,set_status,save_template,list_tasks,results,templates
from dedup import add_task_unique,import_lines,pool_stats,init_dedup
from keenable_adapter import extract_results
st.set_page_config(page_title='LinkedIn 高管挖掘 V6',layout='wide')
password=__import__('os').environ.get('APP_PASSWORD')
if password:
 import hmac
 supplied=st.text_input('访问密码',type='password')
 if not hmac.compare_digest(supplied,password):
  st.info('请输入访问密码后使用共享数据库。')
  st.stop()
init();init_dedup();st.title('LinkedIn 高管链接挖掘助手 V6')
st.caption('持久任务队列 · PostgreSQL 共享历史 · 暂停/恢复 · 规则模板 · 证据导出')
st.warning('后台任务需独立运行 worker.py。LinkedIn 不进行未经授权的自动抓取；没有明确公开证据不计合格。')
config={'cutoff':1990,'us_required':True,'exclude_it':True,'senior_required':True,'surname_required':True}
tabs=st.tabs(['新建任务','任务队列 / 历史','规则模板','跨窗口去重库','Keenable 搜索导入'])
with tabs[0]:
 saved=templates();opts=['默认严格规则']+[x['name'] for x in saved]
 chosen=st.selectbox('使用模板',opts)
 if chosen!='默认严格规则':config=json.loads(next(x['config'] for x in saved if x['name']==chosen))
 cutoff=st.number_input('毕业或开始工作年份 ≤（包含当年）',1900,2026,int(config.get('cutoff',1990)))
 config['cutoff']=int(cutoff)
 st.write('强制：姓氏白名单 AND 美国明确证据 AND 非 IT 高管 AND（毕业≤截止年 OR 工作开始≤截止年）')
 name=st.text_input('任务名称',value='美国非 IT 高管筛选')
 upload=st.file_uploader('CSV / XLSX：url,name,text；或 TXT：每行一个 URL',type=['csv','xlsx','txt'])
 pasted=st.text_area('粘贴 URL（每行一个）')
 if st.button('加入后台队列',type='primary'):
  rows=[]
  if upload:
   raw=upload.getvalue()
   if upload.name.endswith('.xlsx'):rows=pd.read_excel(io.BytesIO(raw)).fillna('').to_dict('records')
   elif upload.name.endswith('.csv'):rows=pd.read_csv(io.BytesIO(raw)).fillna('').to_dict('records')
   else:rows=[{'url':u} for u in parse_links(raw.decode('utf-8-sig',errors='replace'))]
  rows += [{'url':u.strip()} for u in pasted.splitlines() if u.strip()]
  dedup={}
  for r in rows:
   url=str(r.get('url','')).strip()
   if url.startswith(('http://','https://')):dedup[url]={'url':url,'name':str(r.get('name','')),'text':str(r.get('text',''))}
  if not dedup:st.error('请导入有效链接')
  else:
   tid,stats=add_task_unique(name,list(dedup.values()),config)
   st.success(f'任务 #{tid}：新增 {stats["accepted"]} 条，历史重复 {stats["history_duplicates"]} 条，批内重复 {stats["batch_duplicates"]} 条，无效 {stats["invalid"]} 条')
with tabs[1]:
 if st.button('刷新任务状态'):st.rerun()
 tasks=list_tasks()
 if not tasks:st.info('暂无任务')
 else:
  st.dataframe(pd.DataFrame(tasks),use_container_width=True,hide_index=True)
  tid=st.selectbox('查看任务',options=[t['id'] for t in tasks],format_func=lambda x:f'#{x} · '+next(t['name'] for t in tasks if t['id']==x))
  current=next(t for t in tasks if t['id']==tid)
  st.progress(current['done']/current['total'] if current['total'] else 0,text=f"{current['done']}/{current['total']} 已完成 · {current['status']}")
  a,b,c=st.columns(3)
  if a.button('暂停',disabled=current['status'] in ('completed','cancelled')):set_status(tid,'paused');st.rerun()
  if b.button('恢复',disabled=current['status']!='paused'):set_status(tid,'queued');st.rerun()
  if c.button('取消',disabled=current['status'] in ('completed','cancelled')):set_status(tid,'cancelled');st.rerun()
  items=results(tid);flat=[]
  for i in items:
   d=json.loads(i['result']) if i['result'] else {}
   flat.append({'链接':i['url'],'姓名':i['name'],'任务项状态':i['status'],**d})
  df=pd.DataFrame(flat);st.dataframe(df,use_container_width=True,hide_index=True)
  if not df.empty:
   buf=io.BytesIO()
   with pd.ExcelWriter(buf,engine='openpyxl') as w:
    df.to_excel(w,index=False,sheet_name='历史结果')
    if '状态' in df:df[df['状态']=='待人工核验'].to_excel(w,index=False,sheet_name='待核验')
   st.download_button('下载 Excel',buf.getvalue(),f'task_{tid}.xlsx')
   st.download_button('下载 CSV',df.to_csv(index=False).encode('utf-8-sig'),f'task_{tid}.csv')
with tabs[2]:
 st.write('保存可重复使用的筛选规则；任务创建时会保存规则快照。')
 template_name=st.text_input('模板名称')
 template_year=st.number_input('模板截止年份',1900,2026,1990)
 if st.button('保存模板'):
  if template_name.strip():save_template(template_name.strip(),{**config,'cutoff':int(template_year)});st.success('已保存');st.rerun()
  else:st.error('请输入模板名称')
 st.dataframe(pd.DataFrame(templates()),use_container_width=True,hide_index=True)

with tabs[3]:
 st.subheader('全局 LinkedIn 链接去重库')
 count,imports=pool_stats()
 st.metric('已收录唯一 LinkedIn 个人主页',f'{count:,}')
 st.caption('所有任务共享此数据库。历史链接导入后永久参与后续任务去重（取决于数据库持久化）。')
 history_files=st.file_uploader('导入其他聊天窗口导出的历史链接 TXT / CSV（每行一个 LinkedIn URL）',type=['txt','csv'],accept_multiple_files=True,key='dedup_upload')
 if st.button('合并历史链接到全局库'):
  if not history_files:st.warning('请先选择文件')
  else:
   for f in history_files:
    report=import_lines(f.getvalue().decode('utf-8-sig',errors='replace').splitlines(),f.name)
    st.write(f.name,report)
   st.rerun()
 st.dataframe(pd.DataFrame(imports),use_container_width=True,hide_index=True)
 with __import__('storage').connect() as c:
  rejected=[dict(x) for x in c.execute('SELECT task_id,url,canonical_url,reason,created FROM dedup_rejections ORDER BY id DESC LIMIT 1000')]
 if rejected:st.download_button('导出最近重复拒绝记录 CSV',pd.DataFrame(rejected).to_csv(index=False).encode('utf-8-sig'),'dedup_rejections.csv')

with tabs[4]:
 st.subheader('Keenable 公开搜索 · 结果导入')
 st.info('ChatGPT 内 Keenable 搜索插件与外部部署 APP 不共享凭证。这里支持将搜索结果 JSON 导入后台任务，或由你自行配置有授权的外部 API 适配器。')
 st.code('美国公司管理团队高管履历，姓氏 Wang，1990 年或之前毕业或开始工作，非 IT 职位',language='text')
 st.caption('在 ChatGPT 使用 Keenable 搜索后，将返回的结果 JSON（含 results/items、url、title、snippet）粘贴到下方。搜索摘要只作为发现线索，不直接认定符合年份。')
 keenable_json=st.text_area('Keenable 搜索结果 JSON',height=180,key='keenable_json')
 keenable_file=st.file_uploader('或上传搜索结果 JSON',type=['json'],key='keenable_upload')
 keenable_task=st.text_input('导入任务名称',value='Keenable 公开搜索候选')
 if st.button('导入 Keenable 结果并执行全局去重'):
  try:
   raw=keenable_file.getvalue().decode('utf-8-sig') if keenable_file else keenable_json
   rows=extract_results(raw)
   if not rows:st.warning('未发现有效的公开网页 URL')
   else:
    tid,stats=add_task_unique(keenable_task,rows,config)
    st.success(f'任务 #{tid} · 新增 {stats["accepted"]} · 历史重复 {stats["history_duplicates"]} · 批内重复 {stats["batch_duplicates"]}')
  except (ValueError,json.JSONDecodeError) as exc:st.error(f'无法解析结果：{exc}')
 st.caption('Keenable 结果只进入候选队列；最终合格需公开原文证据。不要上传 API 密钥。')
