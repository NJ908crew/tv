"""Catalog helper run on the GitHub runner (which can reach YouTube).

  python3 yt_scrape.py search <artists.txt> <out.json>
      For each artist: searches for official music videos and full live sets
      and records id, title, channel, channel badges, length, views, age.
  python3 yt_scrape.py check <ids.json> <out.json>
      For each {id, ar, song}: embeddable (oEmbed), maxres thumbnail present,
      and (for music videos) the song's first-release year from MusicBrainz.
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


def get(url, headers=None, timeout=25):
    h = {'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9', 'Cookie': 'CONSENT=YES+1; SOCS=CAI'}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.status, r.read().decode('utf-8', 'ignore')


def txt(o):
    if not o: return ''
    return o.get('simpleText') or ''.join(r.get('text', '') for r in o.get('runs', []))


def secs(s):
    if not s: return 0
    n = 0
    for p in s.split(':'): n = n * 60 + int(p)
    return n


def views(s):
    m = re.sub(r'[^\d]', '', s or '')
    return int(m) if m else 0


def search(q):
    url = 'https://www.youtube.com/results?' + urllib.parse.urlencode({'search_query': q, 'sp': 'EgIQAQ=='})  # videos only
    _, h = get(url)
    m = re.search(r'var ytInitialData = (\{.*?\});</script>', h)
    out = []
    if not m: return out

    def walk(o):
        if isinstance(o, dict):
            v = o.get('videoRenderer')
            if v and v.get('videoId'):
                badges = [b.get('metadataBadgeRenderer', {}).get('style', '') for b in v.get('ownerBadges', [])]
                run = (v.get('ownerText') or {}).get('runs', [{}])[0]
                out.append({
                    'id': v['videoId'], 'title': txt(v.get('title')), 'ch': run.get('text', ''),
                    'chid': run.get('navigationEndpoint', {}).get('browseEndpoint', {}).get('browseId', ''),
                    'badges': badges, 's': secs(txt(v.get('lengthText'))),
                    'v': views(txt(v.get('viewCountText'))), 'age': txt(v.get('publishedTimeText')),
                })
                return
            for x in o.values(): walk(x)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(json.loads(m.group(1)))
    return out


def do_search(artists_file, out_file):
    artists = [a.strip() for a in open(artists_file, encoding='utf-8') if a.strip()]
    rows, fails = [], []
    for i, a in enumerate(artists):
        for kind, q in (('v', f'{a} official music video'), ('v', f'{a} official video'), ('l', f'{a} live full set')):
            for attempt in range(3):
                try:
                    res = search(q)
                    for r in res: r.update(artist=a, k=kind, q=q)
                    rows += res
                    break
                except Exception as e:
                    time.sleep(5 * (attempt + 1))
            else:
                fails.append(q)
            time.sleep(1.2)
        print(i + 1, a, len(rows), flush=True)
    json.dump({'rows': rows, 'fails': fails}, open(out_file, 'w'), ensure_ascii=False)


def do_check(ids_file, out_file):
    items = json.load(open(ids_file))
    out = {}
    for i, it in enumerate(items):
        vid = it['id']; r = {}
        try:
            st, _ = get(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json')
            r['e'] = st == 200
        except urllib.error.HTTPError as e:
            r['e'] = False; r['oembed'] = e.code
        except Exception:
            r['e'] = None
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://i.ytimg.com/vi/{vid}/maxresdefault.jpg', method='HEAD'), timeout=15) as x:
                r['maxres'] = x.status == 200
        except Exception:
            r['maxres'] = False
        if it.get('song'):
            try:
                q = f'recording:"{it["song"]}" AND artist:"{it["ar"]}"'
                _, body = get('https://musicbrainz.org/ws/2/recording?fmt=json&limit=25&query=' + urllib.parse.quote(q),
                              headers={'User-Agent': 'OutofStepTV/1.0 (chris@chris-delia.com)'})
                ys = []
                for rec in json.loads(body).get('recordings', []):
                    if rec.get('score', 0) < 90: continue
                    d = rec.get('first-release-date') or ''
                    if re.match(r'\d{4}', d): ys.append(int(d[:4]))
                if ys: r['ry'] = min(ys)
            except Exception:
                pass
            time.sleep(1.1)
        out[vid] = r
        if i % 50 == 0: print(i, flush=True)
    json.dump(out, open(out_file, 'w'))


def do_queries(qfile, out_file):
    """One search per line of qfile; keeps the top 15 results for each."""
    out = {}
    for q in [x.strip() for x in open(qfile, encoding='utf-8') if x.strip()]:
        try: out[q] = search(q)[:15]
        except Exception as e: out[q] = {'error': str(e)}
        time.sleep(1.2)
    json.dump(out, open(out_file, 'w'), ensure_ascii=False)


def do_addskate(spec_file, out_file):
    """For each {id, slugs}: YouTube thumbnail + embed check, and box art + year + runtime from
    the first SkateVideoSite slug that exists. Files land next to out_file."""
    import os
    d = os.path.dirname(out_file); res = {}
    for it in json.load(open(spec_file)):
        vid = it['id']; r = {}
        try:
            st, body = get(f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json')
            r['e'] = True; r['oembed'] = json.loads(body)
        except urllib.error.HTTPError as e: r['e'] = False; r['code'] = e.code
        except Exception as e: r['e'] = None
        for name in ('maxresdefault', 'hqdefault'):
            try:
                with urllib.request.urlopen(urllib.request.Request(f'https://i.ytimg.com/vi/{vid}/{name}.jpg', headers={'User-Agent': UA}), timeout=20) as x:
                    b = x.read()
                if len(b) > 5000:
                    open(os.path.join(d, f'{vid}.thumb.jpg'), 'wb').write(b); r['thumb'] = name; break
            except Exception: pass
        for slug in it.get('slugs', []):
            try:
                _, h = get('https://skatevideosite.com/videos/' + slug)
            except Exception: continue
            m = re.search(r'property="og:image" content="([^"]+)"', h)
            if not m: continue
            r['svs'] = slug; r['cover_url'] = m.group(1)
            y = re.search(r'\b(19[89]\d|20[0-2]\d)\b', re.sub(r'<[^>]+>', ' ', h)[:20000]); r['year_guess'] = y.group(1) if y else None
            mm = re.search(r'(\d+)\s*min', re.sub(r'<[^>]+>', ' ', h)); r['minutes'] = int(mm.group(1)) if mm else None
            try:
                with urllib.request.urlopen(urllib.request.Request(m.group(1), headers={'User-Agent': UA}), timeout=30) as x:
                    ext = m.group(1).rsplit('.', 1)[-1].split('?')[0][:4]
                    open(os.path.join(d, f'{vid}.cover.{ext}'), 'wb').write(x.read()); r['cover'] = f'{vid}.cover.{ext}'
            except Exception as e: r['cover_err'] = str(e)
            break
        res[vid] = r; time.sleep(1)
    json.dump(res, open(out_file, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    {'search': do_search, 'check': do_check, 'queries': do_queries, 'addskate': do_addskate}[sys.argv[1]](sys.argv[2], sys.argv[3])
