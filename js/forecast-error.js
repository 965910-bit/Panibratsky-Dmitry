'use strict';

// Single-observation absolute percentage error for non-negative demand.
(function (root) {
  function number(value) {
    if (typeof value !== 'string') return null;
    const input = value.trim();
    if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(input)) return null;
    const parsed = Number(input);
    return Number.isFinite(parsed) ? parsed : null;
  }
  function ape(actual, forecast) {
    const a = number(actual), f = number(forecast);
    if (a === null || f === null || a <= 0 || f < 0) return null;
    const result = Math.abs(a - f) / a * 100;
    return Number.isFinite(result) ? result : null;
  }
  const api = Object.freeze({ ape });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMForecast = api;
})(typeof window !== 'undefined' ? window : null);
