"""Import exported Keen able/Keenable search results; no ChatGPT plugin credential reuse."""
import json
from urllib.parse import urlsplit


def extract_results(payload):
    if isinstance(payload,str): payload=json.loads(payload)
    if isinstance(payload,list): nodes=payload
    elif isinstance(payload,dict):
        nodes=next((payload[k] for k in ('results','items','pages','data') if isinstance(payload.get(k),list)),None)
        if nodes is None and isinstance(payload.get('data'),dict):
            nodes=next((payload['data'][k] for k in ('results','items','pages') if isinstance(payload['data'].get(k),list)),None)
        if nodes is None: nodes=[payload]
    else: raise ValueError('JSON 必须是结果对象或数组')
    rows=[];seen=set()
    for node in nodes:
        if not isinstance(node,dict):continue
        url=next((node.get(k) for k in ('url','link','page_url','source_url') if isinstance(node.get(k),str)),None)
        if not url:continue
        parts=urlsplit(url)
        if parts.scheme not in ("https","http") or not parts.hostname or parts.username or parts.password:continue
        url=url.strip()
        if url in seen:continue
        seen.add(url)
        title=str(node.get('title') or node.get('name') or '')
        snippet=str(node.get('snippet') or node.get('description') or node.get('content') or '')
        # Search snippets are discovery hints, not verified career evidence.
        rows.append({'url':url,'name':'','text':'','source':'Keenable','search_title':title[:300],'search_snippet':snippet[:1500]})
    return rows
