(function () {
  const storageKey = "mkt-preview-viewport";
  const root = document.documentElement;
  const buttons = document.querySelectorAll("[data-viewport]");
  const VIEWPORT_WIDTH = { desktop: null, tablet: 820, mobile: 390 };

  function getViewportMeta() {
    return (
      document.getElementById("mkt-preview-viewport") ||
      document.querySelector('meta[name="viewport"]')
    );
  }

  function syncViewportMeta(mode) {
    const meta = getViewportMeta();
    if (!meta) return;
    const width = VIEWPORT_WIDTH[mode];
    meta.content =
      width == null
        ? "width=device-width, initial-scale=1.0"
        : `width=${width}, initial-scale=1.0`;
  }

  function notifyResize() {
    window.dispatchEvent(new Event("resize"));
  }

  function applyViewport(mode) {
    root.dataset.mktViewport = mode;
    syncViewportMeta(mode);
    buttons.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.viewport === mode);
    });
    notifyResize();
    try {
      sessionStorage.setItem(storageKey, mode);
    } catch (_) {
      /* ignore */
    }
  }

  const saved = (() => {
    try {
      return sessionStorage.getItem(storageKey);
    } catch (_) {
      return null;
    }
  })();

  applyViewport(saved && ["desktop", "tablet", "mobile"].includes(saved) ? saved : "desktop");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => applyViewport(btn.dataset.viewport));
  });
})();
