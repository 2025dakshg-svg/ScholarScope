/**
 * ScholarScope Copy-to-Clipboard Helper
 */
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("[data-copy-target]").forEach(function(button) {
    button.addEventListener("click", function() {
      const targetId = button.getAttribute("data-copy-target");
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;

      const text = targetEl.innerText || targetEl.textContent;
      navigator.clipboard.writeText(text).then(function() {
        const originalText = button.innerText;
        button.innerText = "Copied!";
        button.setAttribute("aria-live", "polite");
        setTimeout(function() {
          button.innerText = originalText;
        }, 2000);
      }).catch(function(err) {
        console.error("Clipboard copy failed:", err);
      });
    });
  });
});

