'use strict';

// Order-level OTIF: the numerator counts the SAME orders satisfying both criteria.
(function (root) {
  function count(value) {
    if (typeof value === 'string') {
      if (!/^\d+$/.test(value.trim())) return null;
      value = Number(value.trim());
    }
    return Number.isSafeInteger(value) && value >= 0 ? value : null;
  }

  function calculate(completed, total) {
    const success = count(completed);
    const population = count(total);
    if (success === null || population === null || population === 0 || success > population) return null;
    return success / population * 100;
  }

  const api = Object.freeze({ calculate });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMOTIF = api;
})(typeof window !== 'undefined' ? window : null);
