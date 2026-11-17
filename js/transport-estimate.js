'use strict';
(function (root) {
  function parse(value, optional) {
    if (typeof value !== 'string') return null;
    const s = value.trim();
    if (s === '' && optional) return 0;
    if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(s)) return null;
    const n = Number(s);
    if (!Number.isFinite(n) || (n === 0 && /[1-9]/.test(s.split(/[eE]/)[0]))) return null;
    return n;
  }
  function product(a, b) {
    const n = a * b;
    return !Number.isFinite(n) || (a !== 0 && b !== 0 && n === 0) ? null : n;
  }
  function publicEstimate(values) {
    if (!Array.isArray(values) || values.length !== 3) return null;
    const d = parse(values[0]), r = parse(values[1]), extra = parse(values[2], true);
    if (d === null || r === null || extra === null || d <= 0 || r < 0 || extra < 0) return null;
    const base = product(d, r);
    if (base === null || !Number.isFinite(base + extra)) return null;
    return base + extra;
  }
  function ftlEstimate(values) {
    if (!Array.isArray(values) || values.length !== 3) return null;
    const d = parse(values[0]), r = parse(values[1]), coefficient = parse(values[2]);
    if (d === null || r === null || coefficient === null || d <= 0 || r < 0 || coefficient <= 0) return null;
    const base = product(d, r);
    return base === null ? null : product(base, coefficient);
  }
  const api = Object.freeze({publicEstimate, ftlEstimate});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMTransportEstimate = api;
})(typeof window !== 'undefined' ? window : null);
