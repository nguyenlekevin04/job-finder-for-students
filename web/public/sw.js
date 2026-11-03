// Service worker for job alerts (web push). It only shows notifications the daily update
// sends and opens the board when one is tapped. No caching, no offline mode.
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = {};
  }
  event.waitUntil(
    self.registration.showNotification(String(data.title || "New student jobs"), {
      body: String(data.body || ""),
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      tag: "new-jobs", // a newer alert replaces an unread older one
      data: { url: String(data.url || "/") },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  // Only ever open a page of this site, whatever the payload says.
  const target = new URL(event.notification.data?.url || "/", self.location.origin);
  const url = target.origin === self.location.origin ? target.href : self.location.origin + "/";
  event.waitUntil(
    // navigate() works only on tabs this worker controls; otherwise open a new one.
    self.clients.matchAll({ type: "window" }).then((wins) => {
      const open = wins.find((w) => w.url.startsWith(self.location.origin));
      return open
        ? open.navigate(url).then((w) => (w ? w.focus() : self.clients.openWindow(url)), () => self.clients.openWindow(url))
        : self.clients.openWindow(url);
    }),
  );
});
