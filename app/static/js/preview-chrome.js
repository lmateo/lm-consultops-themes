(function () {
  const storageKey = "mkt-preview-viewport";
  const root = document.documentElement;
  const buttons = document.querySelectorAll("[data-viewport]");

  function applyViewport(mode) {
    root.dataset.mktViewport = mode;
    buttons.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.viewport === mode);
    });
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
