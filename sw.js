// SwimIQ サービスワーカー
// 中身を更新したら、この番号を上げること（v18 → v19 → ...）
var CACHE = 'swim-app-v23';
var FILES = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-180.png',
  './icon-192.png',
  './icon-512.png',
  './icon-512-maskable.png',
  './shacchi.png'
];

self.addEventListener('install', function(e){
  e.waitUntil(
    caches.open(CACHE).then(function(c){
      // 1つずつキャッシュする。どれかが無くても全体は失敗させない
      return Promise.all(FILES.map(function(f){
        return c.add(f).catch(function(){});
      }));
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        if(k !== CACHE) return caches.delete(k);
      }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e){
  e.respondWith(
    caches.match(e.request).then(function(res){
      return res || fetch(e.request);
    })
  );
});
