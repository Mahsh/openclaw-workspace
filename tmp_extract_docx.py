import zipfile, re, html
from pathlib import Path
p=Path(r'C:\Users\mahaishou\.openclaw\media\inbound\云侧SDK错误码上报需求---6e1c91b5-9b0d-4394-adbe-15262bee3f03.docx')
with zipfile.ZipFile(p) as z:
    xml=z.read('word/document.xml').decode('utf-8')
paras=[]
for para in re.findall(r'<w:p[\s\S]*?</w:p>', xml):
    texts=[]
    for t in re.findall(r'<w:t[^>]*>([\s\S]*?)</w:t>', para):
        texts.append(html.unescape(t))
    if texts:
        s=''.join(texts).strip()
        if s:
            paras.append(s)
print('\n'.join(paras))
