'use strict';

// Simplified models only; inputs are strings from number fields. No policy rounding.
(function (root) {
  function numbers(values, count) {
    if (!Array.isArray(values) || values.length !== count) return null;
    const out = values.map(value => {
      if (typeof value !== 'string' || !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) return NaN;
      const trimmed = value.trim();
      const n = Number(trimmed);
      if (n === 0 && /[1-9]/.test(trimmed.split(/[eE]/)[0])) return NaN;
      return n;
    });
    return out.every(Number.isFinite) ? out : null;
  }
  function eoq(values) {
    const a = numbers(values, 3);
    if (!a || a.some(n => n <= 0)) return null;
    const result = Math.sqrt(2 * a[0] * a[1] / a[2]);
    return Number.isFinite(result) && result > 0 ? result : null;
  }
  function safetyNormal(values) {
    const a = numbers(values, 3);
    if (!a || a[0] < 0 || a[1] < 0 || !Number.isSafeInteger(a[2]) || a[2] <= 0) return null;
    const result = a[0] * a[1] * Math.sqrt(a[2]);
    return Number.isFinite(result) && (result > 0 || a[0] === 0 || a[1] === 0) ? result : null;
  }
  function safetyScenario(values) {
    const a = numbers(values, 3);
    if (!a || a[0] < 0 || a[1] < 0 || a[0] < a[1] || a[2] <= 0) return null;
    const result = (a[0] - a[1]) * a[2];
    return Number.isFinite(result) && (result > 0 || a[0] === a[1]) ? result : null;
  }
  function reorderPoint(values) {
    const a = numbers(values, 3);
    if (!a || a[0] < 0 || a[1] <= 0 || a[2] < 0) return null;
    const demandDuringLead = a[0] * a[1];
    if (!Number.isFinite(demandDuringLead) || (a[0] > 0 && demandDuringLead === 0)) return null;
    const result = demandDuringLead + a[2];
    return Number.isFinite(result) ? result : null;
  }
  function format(value) {
    if (value !== 0 && (Math.abs(value) < 0.005 || Math.abs(value) >= 1e21)) return value.toExponential(2);
    return value.toFixed(2).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
  }
  const api = Object.freeze({ eoq, safetyNormal, safetyScenario, reorderPoint, format });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMInventory = api;
})(typeof window !== 'undefined' ? window : null);
