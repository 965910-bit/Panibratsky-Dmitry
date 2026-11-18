'use strict';
// Single SKU, deterministic, lost demand; whole units and a bounded horizon.
(function (root) {
  function integer(value, min, max) {
    if (typeof value !== 'string' || !/^\d+$/.test(value.trim())) return null;
    const n = Number(value.trim());
    return Number.isSafeInteger(n) && n >= min && n <= max ? n : null;
  }
  function simulate(values) {
    if (!values || typeof values !== 'object') return null;
    const stock = integer(values.stock, 0, 1000000);
    const demand = integer(values.demand, 0, 1000000);
    const horizon = integer(values.horizon, 1, 30);
    const mainDay = integer(values.mainDay, 1, 365);
    const mainQty = integer(values.mainQty, 0, 1000000);
    const extraDay = integer(values.extraDay, 1, 365);
    const extraQty = integer(values.extraQty, 0, 1000000);
    if ([stock, demand, horizon, mainDay, mainQty, extraDay, extraQty].some(n => n === null)) return null;
    function scenario(includeExtra) {
      let balance = stock, lostTotal = 0, filledTotal = 0, shortageDays = 0, receivedTotal = 0;
      const days = [];
      for (let day = 1; day <= horizon; day++) {
        const received = (day === mainDay ? mainQty : 0) + (includeExtra && day === extraDay ? extraQty : 0);
        receivedTotal += received;
        const available = balance + received;
        const filled = Math.min(available, demand);
        const lost = demand - filled;
        balance = available - filled;
        filledTotal += filled;
        lostTotal += lost;
        if (lost > 0) shortageDays++;
        days.push({ day, received, demand, filled, lost, balance });
      }
      return { days, receivedTotal, requested: demand * horizon, filledTotal, lostTotal, shortageDays, closingStock: balance };
    }
    return { baseline: scenario(false), alternative: scenario(true) };
  }
  const api = Object.freeze({ simulate });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMCaseModel = api;
})(typeof window !== 'undefined' ? window : null);
