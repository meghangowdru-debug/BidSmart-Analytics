import { describe, expect, it } from 'vitest';
import {
  addLocalDaysToDateTime,
  getMinimumAuctionEnd,
  toLocalDateTimeInput,
  toUtcISOString,
  validateAuctionSchedule,
} from '../utils/auctionScheduling';

describe('auction scheduling date/time helpers', () => {
  it('formats the current time for local datetime inputs and converts it back to UTC', () => {
    const now = new Date();
    const localValue = toLocalDateTimeInput(now);
    const parsedLocal = new Date(localValue);

    expect(parsedLocal.getTime()).toBeGreaterThanOrEqual(now.getTime() - 60000);
    expect(toUtcISOString(localValue)).toBe(parsedLocal.toISOString());
  });

  it('rejects start times in the past', () => {
    const now = new Date();
    const past = toLocalDateTimeInput(new Date(now.getTime() - 120000));
    const futureEnd = toLocalDateTimeInput(new Date(now.getTime() + 3600000));

    expect(validateAuctionSchedule(past, futureEnd, now)).toMatch(/start.*cannot be in the past/i);
  });

  it('rejects an end time that is not strictly later than the start', () => {
    const now = new Date();
    const start = toLocalDateTimeInput(new Date(now.getTime() + 120000));

    expect(validateAuctionSchedule(start, start, now)).toMatch(/must be later than the start/i);
  });

  it('moves the minimum end input forward when the start time changes', () => {
    const now = new Date();
    const start = toLocalDateTimeInput(new Date(now.getTime() + 3600000));
    const minEnd = new Date(getMinimumAuctionEnd(start, now));

    expect(minEnd.getTime()).toBeGreaterThan(new Date(start).getTime());
  });

  it('adds calendar days while preserving the local wall-clock time', () => {
    const start = toLocalDateTimeInput(new Date());
    const expected = new Date(start);
    expected.setDate(expected.getDate() + 3);
    const end = addLocalDaysToDateTime(start, 3);

    expect(new Date(end).getTime()).toBe(expected.getTime());
  });
});
