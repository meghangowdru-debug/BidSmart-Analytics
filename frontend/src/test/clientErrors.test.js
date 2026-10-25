import { describe, expect, it } from 'vitest';
import { getErrorMessage } from '../api/client';

describe('getErrorMessage', () => {
  it('explains a response-less network failure instead of showing the raw axios text', () => {
    const message = getErrorMessage({ message: 'Network Error', code: 'ERR_NETWORK', request: {} });

    expect(message).not.toBe('Network Error');
    expect(message).toMatch(/Cannot get a response from the server/);
  });

  it('explains a timeout', () => {
    expect(getErrorMessage({ message: 'timeout of 15000ms exceeded', code: 'ECONNABORTED' }))
      .toMatch(/took too long/);
  });

  it('keeps backend detail messages', () => {
    expect(getErrorMessage({ response: { status: 503, data: { detail: 'Schema is missing' } } }))
      .toBe('Schema is missing');
  });
});
