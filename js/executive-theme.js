// Apply the same saved theme as the home page before the page is painted.
try {
  document.documentElement.dataset.executiveTheme = localStorage.getItem('executive-theme') === 'light' ? 'light' : 'dark';
} catch (_) {
  document.documentElement.dataset.executiveTheme = 'dark';
}
