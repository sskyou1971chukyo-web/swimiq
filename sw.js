// SwimIQ サービスワーカー v3
// 役割：画像などをたくわえて表示を速くする。
// 大事な作り：.html で終わるもの（記録アプリ・分析アプリの両方）は
//             「ネット優先」＋「古い写しは使わず必ず取り直す」。
//             v2 では index.html だけがその扱いで、swimrec_app.html が
//             古い写しのまま居座ってしまう不具合がありました。
// 新しい版が出たら、次にひらいたときに ちゃんと新しいほうが届く。
// 電波が無いときだけ、たくわえてあった写しをつかう。

var CACHE = 'swimiq-v3';  // ← 名前を変えると、古いたくわえ(v2まで)がまとめて片付く

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

  // 終わりが / か .html のものは、どれもアプリ本体としてあつかう
  var isApp = url.pathname.endsWith('/') || url.pathname.endsWith('.html');
  if(isApp){
    // アプリ本体：まずネットへ。ここで {cache:'no-store'} を付けて、
    // 「古い写しは使わず、必ず新しいのを取ってくる」ようにする（iPhone対策）。
    e.respondWith(
      fetch(e.request, { cache: 'no-store' }).then(function(res){
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
