(function () {
  const storageKey = "mkt-preview-viewport";
  const root = document.documentElement;
  const buttons = document.querySelectorAll("[data-viewport]");
  const VIEWPORT_WIDTH = { desktop: null, tablet: 820, mobile: 390 };

  function normalizeHeaderBrandPlacement() {
    document.querySelectorAll(".mkt-preview-canvas header .navbar").forEach((navbar) => {
      const brand = navbar.querySelector(".navbar-brand");
      if (!brand) return;

      const homeLink = Array.from(navbar.querySelectorAll("a.nav-link, a"))
        .find((anchor) => anchor.textContent.trim().toLowerCase() === "home");
      if (!homeLink) return;

      const navbarContainer = brand.closest(".container, .container-fluid");
      if (!navbarContainer || !navbarContainer.contains(homeLink)) return;

      const brandWrapper = brand.parentElement;
      const moveNode =
        brandWrapper &&
        brandWrapper.tagName === "DIV" &&
        brandWrapper.parentElement === navbarContainer
          ? brandWrapper
          : brand;

      const homeWrapper =
        homeLink.closest("li") || homeLink.closest("div") || homeLink;
      if (!homeWrapper || !navbarContainer.contains(homeWrapper)) return;

      // Ensure logo appears before Home across all live preview headers.
      if (
        moveNode.compareDocumentPosition(homeWrapper) &
        Node.DOCUMENT_POSITION_FOLLOWING
      ) {
        return;
      }

      navbarContainer.insertBefore(moveNode, navbarContainer.firstElementChild);
    });
  }

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

  function refreshEmbeddedLayout() {
    window.dispatchEvent(new Event("resize"));
    window.dispatchEvent(new Event("orientationchange"));

    if (typeof window.Swiper !== "undefined") {
      document.querySelectorAll(".mkt-preview-canvas .swiper").forEach((el) => {
        if (el.swiper && typeof el.swiper.update === "function") {
          el.swiper.update();
        }
      });
    }

    if (typeof window.jQuery !== "undefined") {
      try {
        window.jQuery(window).trigger("resize");
      } catch (_) {
        /* ignore */
      }
    }
  }

  function applyViewport(mode) {
    normalizeHeaderBrandPlacement();
    root.dataset.mktViewport = mode;
    syncViewportMeta(mode);
    buttons.forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.viewport === mode);
    });

    requestAnimationFrame(() => {
      refreshEmbeddedLayout();
      requestAnimationFrame(refreshEmbeddedLayout);
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

  applyViewport(
    saved && ["desktop", "tablet", "mobile"].includes(saved) ? saved : "desktop"
  );

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => applyViewport(btn.dataset.viewport));
  });
})();
