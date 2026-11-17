'use strict';

// Unrounded comparison for one package. Contract terms and carrier rounding are not applied.
(function (root) {
  function compare(values) {
    if (!Array.isArray(values) || values.length !== 5) return null;
    const numbers = values.map(value => {
      if (typeof value !== 'string' || !/^[+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) return NaN;
      return Number(value.trim());
    });
    if (numbers.some(value => !Number.isFinite(value) || value <= 0)) return null;
    const [length, width, height, actual, divisor] = numbers;
    const volume = length * width * height;
    const dimensional = volume / divisor;
    if (!Number.isFinite(volume) || !Number.isFinite(dimensional) || dimensional <= 0) return null;
    return Math.max(actual, dimensional);
  }
  const api = Object.freeze({ compare });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMDimensionalWeight = api;
})(typeof window !== 'undefined' ? window : null);
