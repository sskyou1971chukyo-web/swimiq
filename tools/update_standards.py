#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日本水泳連盟の 標準記録の ページを 読み、standards.json を 作り直します。
GitHub Actions が 毎日 1回 動かします（.github/workflows/standards.yml）。

決まりごと
 - 大会の 一覧は https://aquatics.or.jp/swim/ の「標準記録」の リンクから 取ります。
 - いちばん 新しい 年度と、その 前の 年度の 大会の ページを 読みます。
 - ページの 中の 見出しと 表だけを 取り出して 入れます。数字の 読み取りは アプリが します
   （アプリと 同じ 読み方に するため）。
 - 読めた 大会が 少なすぎる ときや、読めなかった ときは、前の standards.json を そのまま 残します。
"""
import json, re, sys, os, time, datetime, urllib.request

INDEX = 'https://aquatics.or.jp/swim/'
UA = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ja,en;q=0.8',
}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')

def strip_tags(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()

def parse_index(html):
    by = {}
    for m in re.finditer(r'<a\b[^>]*href="([^"]*?/swim/japan_record/(\d{4})/(\d+)/?)"[^>]*>(.*?)</a>', html, re.S | re.I):
        year, no = int(m.group(2)), int(m.group(3))
        url = 'https://aquatics.or.jp/swim/japan_record/%d/%02d/' % (year, no)
        title = strip_tags(m.group(4))
        if not title:
            continue
        # 同じ ページへの リンクが いくつか あるときは、いちばん 長い 名前（大会名と 日付が 入った もの）を 使います
        if url not in by or len(title) > len(by[url]['title']):
            by[url] = {'url': url, 'year': year, 'no': no, 'title': title}
    out = list(by.values())
    out.sort(key=lambda x: (-x['year'], x['no']))
    return out

def tables_only(html):
    """見出し（h1〜h6）と 表（table）だけを、ページの 順番どおりに 取り出します"""
    body = re.sub(r'<(script|style|nav|header|footer)\b.*?</\1>', '', html, flags=re.S | re.I)
    parts = [m.group(0) for m in re.finditer(r'<h[1-6]\b[^>]*>.*?</h[1-6]>|<table\b.*?</table>', body, re.S | re.I)]
    return '\n'.join(parts)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(os.path.dirname(here), 'standards.json')
    old = None
    try:
        old = json.load(open(out_path, encoding='utf-8'))
    except Exception:
        pass
    try:
        idx = parse_index(fetch(INDEX))
    except Exception as e:
        print('index fetch failed:', e)
        return 0
    if len(idx) < 3:
        print('too few meets in index, keep old file')
        return 0
    years = sorted({x['year'] for x in idx}, reverse=True)[:2]
    pages, ng = {}, 0
    for it in idx:
        if it['year'] not in years:
            continue
        try:
            h = tables_only(fetch(it['url']))
            if '<table' not in h.lower():
                raise ValueError('no table')
            pages[it['url']] = {'html': h}
        except Exception as e:
            ng += 1
            print('page failed:', it['url'], e)
            if old and it['url'] in (old.get('pages') or {}):
                pages[it['url']] = old['pages'][it['url']]   # 前に 読めた ものを 残します
        time.sleep(1)   # 相手の サイトに 負担を かけないように 1秒 あけます
    if len(pages) < 3:
        print('too few pages, keep old file')
        return 0
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    data = {
        'format': 1,
        'source': 'https://aquatics.or.jp/swim/#standard-record',
        'fetchedAt': now.strftime('%Y-%m-%dT%H:%M:%S+09:00'),
        'list': [x for x in idx if x['year'] in years],
        'pages': pages,
        'failed': ng,
    }
    # 中身が 前と 同じなら 書きかえません（読んだ 時刻だけの 変更で 毎日 書きこまないため）
    if old and old.get('list') == data['list'] and old.get('pages') == data['pages']:
        print('no change')
        return 0
    json.dump(data, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('updated', len(pages), 'pages')
    return 0

if __name__ == '__main__':
    sys.exit(main())
