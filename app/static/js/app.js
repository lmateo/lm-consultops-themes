document.addEventListener("DOMContentLoaded", () => {
  const lazyFrames = document.querySelectorAll("iframe[loading='lazy']");
  lazyFrames.forEach((frame) => frame.setAttribute("title", frame.getAttribute("title") || "Preview frame"));

  document.querySelectorAll(".mkt-thumb-stack").forEach((stack) => {
    const buttons = stack.querySelectorAll("button");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        buttons.forEach((peer) => peer.classList.remove("is-active"));
        button.classList.add("is-active");
      });
    });
  });
});
