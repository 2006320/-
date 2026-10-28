from keenable_adapter import extract_results

def test_results():
    rows=extract_results({'results':[{'url':'https://example.com/leader','title':'Leader','snippet':'1990'},{'url':'https://example.com/leader'}]})
    assert len(rows)==1
    assert rows[0]['text']==''
    assert rows[0]['source']=='Keenable'
