// SwimIQ サービスワーカー v2
// 役割：画像などをたくわえて表示を速くする。
// 大事な作り：index.html（アプリ本体）は「ネット優先」＋「古い写しは使わず必ず取り直す」。
// 新しい版が出たら、次にひらいたときに ちゃんと新しいほうが届く。
// 電波が無いときだけ、たくわえてあった写しをつかう。

var CACHE = 'swimiq-v2';  // ← 名前を変えると、古いたくわえ(v1)がまとめて片付く

self.addEventListener('install', function(e){
  self.skipWaiting();  // 新しいサービスワーカーは すぐ交代する
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.filter(function(k){ return k!==CACHE; })
        .map(function(k){ return caches.delete(k); }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e){
  var url = new URL(e.request.url);
  // よそのサイトへの通信（GASやGitHubなど）には いっさい手を出さない
  if(e.request.method !== 'GET' || url.origin !== location.origin) return;

  var isApp = url.pathname.endsWith('/') || url.pathname.endsWith('index.html');
  if(isApp){
    // アプリ本体：まずネットへ。ここで {cache:'no-store'} を付けて、
    // 「古い写しは使わず、必ず新しいのを取ってくる」ようにする（iPhone対策）。
    e.respondWith(
      fetch(url.pathname, { cache: 'no-store' }).then(function(res){
        var copy = res.clone();
        caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
        return res;
      }).catch(function(){
        // 電波が無いときだけ、たくわえてあった写しをつかう
        return caches.match(e.request);
      })
    );
  } else {
    // 画像など：まず写し。無ければネットからとって写しに足す。
    e.respondWith(
      caches.match(e.request).then(function(hit){
        return hit || fetch(e.request).then(function(res){
          var copy = res.clone();
          caches.open(CACHE).then(function(c){ c.put(e.request, copy); });
          return res;
        });
      })
    );
  }
});
