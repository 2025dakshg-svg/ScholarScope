/**
 * ScholarScope Theme Controller
 * Supports system prefers-color-scheme with manual localStorage persistence.
 */
(function() {
  const STORAGE_KEY = "scholarscope-theme";
  const root = document.documentElement;

  function getPreferredTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlTheme = urlParams.get("theme");
    if (urlTheme === "dark" || urlTheme === "light") {
      return urlTheme;
    }
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") {
      return saved;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      root.setAttribute("data-theme", "dark");
    } else {
      root.setAttribute("data-theme", "light");
    }
    updateToggleButton(theme);
  }

  function updateToggleButton(theme) {
    const btn = document.getElementById("theme-toggle-btn");
    if (!btn) return;
    const isDark = theme === "dark";
    btn.setAttribute("aria-label", isDark ? "Switch to light theme" : "Switch to dark theme");
    btn.setAttribute("aria-pressed", isDark ? "true" : "false");
    btn.innerHTML = isDark
      ? '<svg class="theme-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>'
      : '<svg class="theme-icon" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
  }

  // Apply immediately to avoid flash of incorrect theme
  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  document.addEventListener("DOMContentLoaded", function() {
    updateToggleButton(getPreferredTheme());
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) {
      btn.addEventListener("click", function() {
        const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
        const next = current === "dark" ? "light" : "dark";
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
      });
    }

    // Listen for OS theme changes if user has not set an explicit override
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function(e) {
      if (!localStorage.getItem(STORAGE_KEY)) {
        applyTheme(e.matches ? "dark" : "light");
      }
    });
  });
})();
