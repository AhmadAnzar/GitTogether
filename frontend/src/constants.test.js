import { describe, expect, it } from 'vitest';
import { AVAILABILITY, FILTERS, initials, shortHash } from './constants.js';

describe('initials', () => {
  it('uses the first letter of the first two words', () => {
    expect(initials('Ayesha Khan')).toBe('AK');
    expect(initials('ayesha khan siddiqui')).toBe('AK');
  });

  it('handles single names and extra whitespace', () => {
    expect(initials('  Rohan  ')).toBe('R');
    expect(initials('Meera   Nair')).toBe('MN');
  });
});

describe('shortHash', () => {
  it('returns a stable 7-character hex string', () => {
    expect(shortHash(1)).toMatch(/^[0-9a-f]{7}$/);
    expect(shortHash(42)).toBe(shortHash(42));
  });

  it('gives different profiles different hashes', () => {
    const hashes = new Set([1, 2, 3, 4, 5, 100, 1000].map(shortHash));
    expect(hashes.size).toBe(7);
  });
});

describe('filters', () => {
  it('offer every availability value plus "everyone"', () => {
    const values = FILTERS.map((f) => f.value);
    expect(values).toEqual(['ALL', ...Object.keys(AVAILABILITY)]);
  });
});
