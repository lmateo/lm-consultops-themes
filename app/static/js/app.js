document.addEventListener("DOMContentLoaded", () => {
  const lazyFrames = document.querySelectorAll("iframe[loading='lazy']");
  lazyFrames.forEach((frame) => frame.setAttribute("title", frame.getAttribute("title") || "Preview frame"));
});
