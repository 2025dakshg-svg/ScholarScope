/**
 * ScholarScope Mobile Navigation Toggle
 */
document.addEventListener("DOMContentLoaded", function() {
  const toggleBtn = document.getElementById("mobile-nav-toggle");
  const drawer = document.getElementById("mobile-drawer");

  if (!toggleBtn || !drawer) return;

  toggleBtn.addEventListener("click", function() {
    const isExpanded = toggleBtn.getAttribute("aria-expanded") === "true";
    toggleBtn.setAttribute("aria-expanded", !isExpanded);
    drawer.classList.toggle("open", !isExpanded);
  });

  // Close drawer if user resizes back to desktop viewport
  window.addEventListener("resize", function() {
    if (window.innerWidth > 768 && drawer.classList.contains("open")) {
      drawer.classList.remove("open");
      toggleBtn.setAttribute("aria-expanded", "false");
    }
  });
});

