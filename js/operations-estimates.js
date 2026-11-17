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
  function product(a, b) {
    const n = a * b;
    return !Number.isFinite(n) || (a !== 0 && b !== 0 && n === 0) ? null : n;
  }
  function divide(a, b) {
    if (b === 0) return null;
    const n = a / b;
    return !Number.isFinite(n) || (a !== 0 && n === 0) ? null : n;
  }
  // Exact decimal rational arithmetic prevents an extra unit from binary floating
  // point rounding at a whole-number boundary. Bounds also limit BigInt work.
  function decimal(value) {
    const match = value.trim().match(/^([+-]?)(\d*\.?\d+|\d+\.?)(?:[eE]([+-]?\d+))?$/);
    if (!match) return null;
    const parts = match[2].split('.');
    const digits = parts.join('');
    const exp = Number(match[3] || 0) - (parts[1] || '').length;
    if (digits.length > 100 || !Number.isSafeInteger(exp) || Math.abs(exp) > 100) return null;
    let numerator = BigInt(digits) * (match[1] === '-' ? -1n : 1n);
    let denominator = 1n;
    if (exp >= 0) numerator *= 10n ** BigInt(exp);
    else denominator = 10n ** BigInt(-exp);
    return [numerator, denominator];
  }
  function isExactSafeInteger(value, number) {
    const fraction = decimal(value);
    return Number.isSafeInteger(number) && fraction !== null && fraction[0] % fraction[1] === 0n &&
      fraction[0] / fraction[1] === BigInt(number);
  }
  function exactCount(id, values) {
    const a = values.map(decimal);
    if (a.some(x => x === null)) return null;
    const mul = (x, y) => [x[0] * y[0], x[1] * y[1]];
    const div = (x, y) => [x[0] * y[1], x[1] * y[0]];
    let fraction;
    if (id === 'staff_driver') {
      fraction = div(mul(mul(a[0], a[1]), a[4]), mul(mul(a[2], a[3]), [3600n, 1n]));
    } else if (id === 'pallet_needs') {
      fraction = div(mul(a[0], a[2]), a[1]);
    } else {
      const margin = [a[2][0] * a[1][1] - a[1][0] * a[2][1], a[2][1] * a[1][1]];
      if (margin[0] <= 0n) return null;
      fraction = div(a[0], margin);
    }
    const [n, d] = fraction;
    if (n < 0n || d <= 0n) return null;
    const count = (n + d - 1n) / d;
    return count <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(count) : null;
  }
  function calculate(id, values) {
    const counts = {staff_driver:5, gmroi:2, ccc:3, roi_automation:2, space_util:2, pallet_needs:3, productivity:2, courier_cost:3, order_cycle:3, bep_warehouse:3};
    if (!Object.prototype.hasOwnProperty.call(counts, id)) return null;
    const v = parse(values, counts[id]);
    if (!v) return null;
    switch (id) {
      case 'staff_driver': {
        if (!isExactSafeInteger(values[0], v[0]) || v[0] < 0 || v[1] <= 0 || v[2] <= 0 || v[3] <= 0 || v[4] < 1) return null;
        return exactCount(id, values);
      }
      case 'gmroi':
        return v[1] <= 0 ? null : divide(v[0], v[1]);
      case 'ccc': {
        if (v.some(n => n < 0)) return null;
        const sum = v[0] + v[1];
        const result = sum - v[2];
        return Number.isFinite(sum) && Number.isFinite(result) ? result : null;
      }
      case 'roi_automation': {
        if (v[1] <= 0) return null;
        const net = v[0] - v[1];
        if (!Number.isFinite(net)) return null;
        const fraction = divide(net, v[1]);
        return fraction === null ? null : product(fraction, 100);
      }
      case 'space_util': {
        if (!v.every((n, i) => isExactSafeInteger(values[i], n)) || v[0] < 0 || v[1] <= 0 || v[0] > v[1]) return null;
        const ratio = divide(v[0], v[1]);
        return ratio === null ? null : product(ratio, 100);
      }
      case 'pallet_needs': {
        if (!isExactSafeInteger(values[0], v[0]) || !isExactSafeInteger(values[1], v[1]) || v[0] < 0 || v[1] <= 0 || v[2] < 1) return null;
        return exactCount(id, values);
      }
      case 'productivity':
        return !isExactSafeInteger(values[0], v[0]) || v[0] < 0 || v[1] <= 0 ? null : divide(v[0], v[1]);
      case 'courier_cost': {
        if (v[0] <= 0 || v[1] < 0 || v[2] < 0) return null;
        const cost = product(v[0], v[1]);
        return cost === null ? null : Math.max(cost, v[2]);
      }
      case 'order_cycle': {
        if (v.some(n => n < 0)) return null;
        const first = v[0] + v[1];
        const result = first + v[2];
        return Number.isFinite(first) && Number.isFinite(result) ? result : null;
      }
      case 'bep_warehouse': {
        if (v[0] < 0 || v[1] < 0 || v[2] <= v[1]) return null;
        return exactCount(id, values);
      }
    }
    return null;
  }
  const api = Object.freeze({ calculate });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.SCMOperationsEstimates = api;
})(typeof window !== 'undefined' ? window : null);
