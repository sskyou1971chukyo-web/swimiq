#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界記録・日本記録を公式の一覧（Wikipediaの記録一覧ページ。World Aquatics / 日本水泳連盟の公認記録を転記したもの）
から読み、records.json を更新します。GitHub Actions が週に1回 動かします。

決まりごと
 - いまの records.json にある記録は消しません（保持者の記録として残します）。
 - 新しい記録が見つかったら 1件 足し、同じ種目の古い記録は current を false にします。
 - ラップ（splits）やストロークは、人が出どころ付きで入れたものだけです。ここでは触りません。
 - 読めた記録が少なすぎる（ページの形が変わった）ときは、何も書きかえずに終わります。
"""
import json, re, sys, urllib.request, html, datetime
from html.parser import HTMLParser

SRC = {
  'WR': 'https://en.wikipedia.org/wiki/List_of_world_records_in_swimming',
  'JR': 'https://en.wikipedia.org/wiki/List_of_Japanese_records_in_swimming',
}
UA = {'User-Agent': 'SwimIQ-records-bot/1.0 (https://sskyou1971chukyo-web.github.io/swimiq/)'}
EVMAP = [('individual medley','im'),('medley','im'),('freestyle','free'),('backstroke','back'),('breaststroke','breast'),('butterfly','fly')]

class Tables(HTMLParser):
    """見出し（h2/h3）と表（table）を順番に拾う かんたんな読み取り"""
    def __init__(self):
        super().__init__(); self.items=[]; self.cur=None; self.row=None; self.cell=None; self.hd=None; self.tag_stack=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('h2','h3','h4'): self.hd=[tag,'']
        elif tag=='table': self.cur=[]
        elif tag=='tr' and self.cur is not None: self.row=[]
        elif tag in ('td','th') and self.row is not None: self.cell=''
        elif tag=='br' and self.cell is not None: self.cell+=' '
    def handle_endtag(self, tag):
        if tag in ('h2','h3','h4') and self.hd: self.items.append(('h', self.hd[0], re.sub(r'\s+',' ',self.hd[1]).strip())); self.hd=None
        elif tag in ('td','th') and self.cell is not None and self.row is not None: self.row.append(re.sub(r'\s+',' ',self.cell).strip()); self.cell=None
        elif tag=='tr' and self.row is not None and self.cur is not None: self.cur.append(self.row); self.row=None
        elif tag=='table' and self.cur is not None: self.items.append(('t', self.cur)); self.cur=None
    def handle_data(self, data):
        if self.hd: self.hd[1]+=data
        if self.cell is not None: self.cell+=data

def fetch(url):
    req=urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r: return r.read().decode('utf-8','replace')

def parse_time(s):
    m=re.search(r'(\d{1,2}:)?\d{1,2}\.\d{2}', s)
    if not m: return None
    t=m.group(0); p=t.split(':')
    return (t, round(float(p[0])*60+float(p[1]),2) if len(p)==2 else round(float(t),2))

def parse_date(s):
    s=s.replace('\xa0',' ')
    for fmt in ('%d %B %Y','%B %d, %Y','%Y-%m-%d','%d %b %Y'):
        try: return datetime.datetime.strptime(s.strip(), fmt).strftime('%Y-%m-%d')
        except Exception: pass
    m=re.search(r'(\d{1,2}) (\w+) (\d{4})', s)
    if m:
        try: return datetime.datetime.strptime(m.group(0), '%d %B %Y').strftime('%Y-%m-%d')
        except Exception: pass
    return None

def parse_event(s):
    s=s.lower()
    if 'relay' in s or '×' in s or ' x ' in s: return None
    m=re.search(r'(\d{2,4})\s*m', s)
    if not m: return None
    dist=int(m.group(1))
    for k,v in EVMAP:
        if k in s: return (v, dist)
    return None

def parse_page(scope, text):
    p=Tables(); p.feed(text)
    course=None; sex=None; out=[]
    for it in p.items:
        if it[0]=='h':
            h=it[2].lower()
            if 'long course' in h or '50 m' in h or '50m' in h: course='LCM'
            elif 'short course' in h or '25 m' in h or '25m' in h: course='SCM'
            if h.startswith('men') or h.startswith('male'): sex='M'
            elif h.startswith('women') or h.startswith('female'): sex='F'
            continue
        rows=it[1]
        if not rows or len(rows)<2: continue
        head=[c.lower() for c in rows[0]]
        if not any('event' in c for c in head) or not any('time' in c for c in head): continue
        if not course or not sex: continue
        ie=[i for i,c in enumerate(head) if 'event' in c][0]
        it_=[i for i,c in enumerate(head) if 'time' in c][0]
        iname=[i for i,c in enumerate(head) if 'name' in c or 'swimmer' in c]
        inat=[i for i,c in enumerate(head) if 'nation' in c]
        idate=[i for i,c in enumerate(head) if 'date' in c]
        imeet=[i for i,c in enumerate(head) if 'meet' in c]
        iplace=[i for i,c in enumerate(head) if 'location' in c or 'place' in c]
        for r in rows[1:]:
            if len(r)<=it_: continue
            ev=parse_event(r[ie]); tm=parse_time(r[it_])
            if not ev or not tm: continue
            pending=('#' in r[ie]) or ('#' in r[it_]) or ('pending' in ' '.join(r).lower()) or ('awaiting' in ' '.join(r).lower())
            def g(idx): return r[idx[0]] if idx and len(r)>idx[0] else ''
            name=re.sub(r'\[.*?\]','',g(iname)).strip()
            out.append({'scope':scope,'course':course,'sex':sex,'event':ev[0],'dist':ev[1],'time':tm[0],'sec':tm[1],
                        'name':name,'nation':g(inat)[:40],'date':parse_date(g(idate)) or '','meet':g(imeet)[:80],'place':g(iplace)[:60],'pending':pending})
    return out

def main():
    path=sys.argv[1] if len(sys.argv)>1 else 'records.json'
    data=json.load(open(path, encoding='utf-8'))
    recs=data['records']
    found=[]
    for scope,url in SRC.items():
        try: text=fetch(url)
        except Exception as e: print('fetch failed', scope, e); return 0
        got=parse_page(scope, text)
        print(scope, len(got), 'rows')
        if len(got)<60: print('too few rows, abort'); return 0
        found+=got
    # 名前の 日本語は、いまの データから 引きつぎます
    ja={}; meetja={}
    for r in recs:
        if r.get('name') and r.get('nameJa'): ja[r['name']]=r['nameJa']
        if r.get('meet') and r.get('meetJa'): meetja[r['meet']]=r['meetJa']
    added=0; changed=False
    for f in found:
        key=(f['scope'],f['course'],f['sex'],f['event'],f['dist'])
        same=[r for r in recs if (r['scope'],r['course'],r['sex'],r['event'],r['dist'])==key]
        exist=[r for r in same if abs(r['sec']-f['sec'])<0.001 and (r['name']==f['name'] or not f['name'])]
        if exist:
            continue
        cur=[r for r in same if r.get('current')]
        # 公認待ちでない 新記録が 見つかった ときだけ、いまの 記録を 入れかえます
        if not f['pending'] and (not cur or f['sec']<min(c['sec'] for c in cur)-0.001):
            for c in cur: c['current']=False; c['note']=(c.get('note') or '') or 'その後に更新された記録'
        rid='%s_%s_%s_%s_%d_%s_%s'%(f['scope'],f['course'],f['sex'],f['event'],f['dist'],f['date'] or 'nodate',re.sub(r'[^A-Za-z]','',f['name'])[:12])
        if any(r['id']==rid for r in recs): rid+='_b'
        recs.append({'id':rid,'scope':f['scope'],'course':f['course'],'sex':f['sex'],'event':f['event'],'dist':f['dist'],'time':f['time'],'sec':f['sec'],
                     'name':f['name'],'nameJa':ja.get(f['name'],''),'nation':f['nation'],'date':f['date'],'meet':f['meet'],'meetJa':meetja.get(f['meet'],''),'place':f['place'],
                     'current': not f['pending'] and (not cur or f['sec']<min(c['sec'] for c in cur)-0.001),'pending':f['pending'],
                     'note':'公認待ち' if f['pending'] else '自動更新で追加（Wikipediaの記録一覧による）','sources':[SRC[f['scope']]],'splits':None,'strokes':None,'splitSource':''})
        added+=1; changed=True
    if changed:
        data['updated']=datetime.date.today().strftime('%Y-%m-%d')
        json.dump(data, open(path,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        print('added', added)
    else:
        print('no change')
    return 0

if __name__=='__main__': sys.exit(main())
