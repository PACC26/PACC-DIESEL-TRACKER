import json, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

URL='https://www.vivaenergy.com.au/quick-links/terminal-gate-pricing'
OUT=Path(__file__).with_name('data.json')
req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 (compatible; PACC-TGP-Tracker/1.0)','Cache-Control':'no-cache'})
with urllib.request.urlopen(req,timeout=30) as response:
    html=response.read().decode('utf-8','replace')
soup=BeautifulSoup(html,'html.parser')
text=soup.get_text(' ',strip=True)
m=re.search(r'Terminal Gate Pricing\s*\(TGP\)\s*as at\s*(\d{1,2}\s+[A-Za-z]+\s+20\d{2})',text,re.I)
if not m: raise RuntimeError('Could not identify Viva published pricing date; retaining last good data')
published=datetime.strptime(m.group(1),'%d %b %Y').date().isoformat()
price=None
for table in soup.find_all('table'):
    rows=table.find_all('tr')
    if not rows: continue
    headers=[c.get_text(' ',strip=True).lower() for c in rows[0].find_all(['th','td'])]
    diesel_idx=next((i for i,h in enumerate(headers) if h.strip()=='diesel'),None)
    if diesel_idx is None: continue
    for row in rows[1:]:
        cells=[c.get_text(' ',strip=True) for c in row.find_all(['td','th'])]
        if any(c.strip().upper()=='MELBOURNE' for c in cells) and diesel_idx<len(cells):
            value=cells[diesel_idx].replace(',','').strip()
            if re.fullmatch(r'\d{2,3}(?:\.\d{1,3})?',value): price=float(value)
            break
    if price is not None: break
if price is None or not 80<=price<=500: raise RuntimeError('Could not safely parse Melbourne Diesel column; retaining last good data')
old=json.loads(OUT.read_text()) if OUT.exists() else {'history':[]}
history=old.get('history',[])
# A new published date supersedes a previous observation for that date.
history=[h for h in history if h['date']!=published]
history.append({'date':published,'price':price})
history=sorted(history,key=lambda h:h['date'])[-365:]
result={'supplier':'Viva Energy','city':'Melbourne','fuel':'Diesel','price_cpl':price,'published_date':published,'checked_at':datetime.now(timezone.utc).isoformat(),'source':URL,'history':history}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print('Updated:',published,price,'c/L')

# Detect a genuine change in the published diesel price
previous_price = old.get('price_cpl')

if previous_price is not None and round(float(previous_price), 2) != round(float(price), 2):
    difference = round(float(price) - float(previous_price), 2)
    direction = "INCREASE" if difference > 0 else "DECREASE"

    print("DIESEL PRICE CHANGE DETECTED")
    print("Previous:", previous_price, "c/L")
    print("New:", price, "c/L")
    print("Movement:", direction, abs(difference), "c/L")
