/**
 * Limpia service workers y cachés heredados de otros proyectos en el mismo
 * origen (p. ej. JustColmado en localhost:3000). El navegador solicita /sw.js
 * periódicamente; este script se auto-desregistra tras purgar.
 */
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const cacheKeys = await caches.keys();
      await Promise.all(cacheKeys.map((key) => caches.delete(key)));
      await self.registration.unregister();
      const clients = await self.clients.matchAll({ type: "window" });
      for (const client of clients) {
        client.navigate(client.url);
      }
    })(),
  );
});
