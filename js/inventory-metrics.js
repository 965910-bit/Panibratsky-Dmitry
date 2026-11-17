'use strict';
(function (root) {
  function parse(values, count) {
    if (!Array.isArray(values) || values.length !== count) return null;
    const result = values.map(value => {
      if (typeof value !== 'string') return NaN;
      const s = value.trim();
      if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(s)) return NaN;
      const n = Number(s);
      if (n === 0 && /[1-9]/.test(s.split(/[eE]/)[0])) return NaN;
      return n;
    });
    return result.every(Number.isFinite) ? result : null;
  }
  function turnover(values) {
    const v = parse(values, 3);
    if (!v || v[0] < 0 || v[1] <= 0 || !Number.isSafeInteger(v[2]) || v[2] <= 0) return null;
    const ratio = v[0] / v[1];
    if (!Number.isFinite(ratio) || (v[0] > 0 && ratio === 0)) return null;
    return ratio;
  }
  function turnoverDays(values) {
    const ratio = turnover(values);
    if (ratio === null) return null;
    if (ratio === 0) return { ratio, days: null };
    const days = Number(values[2]) / ratio;
    if (!Number.isFinite(days) || days <= 0) return null;
    return { ratio, days };
  }
  function fillRate(values, mode) {
    const v = parse(values, 2);
    if (!v || v[0] <= 0 || v[1] < 0 || v[1] > v[0] || !['fulfilled', 'shortage'].includes(mode)) return null;
    const supplied = mode === 'fulfilled' ? v[1] : v[0] - v[1];
    const fraction = supplied / v[0];
    const result = fraction * 100;
    if (!Number.isFinite(result) || (supplied > 0 && (fraction === 0 || result === 0))) return null;
    return result;
  }
  const api = Object.freeze({ turnover, turnoverDays, fillRate });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMInventoryMetrics = api;
})(typeof window !== 'undefined' ? window : null);
