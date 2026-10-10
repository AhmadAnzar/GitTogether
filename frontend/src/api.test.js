import { afterEach, describe, expect, it, vi } from 'vitest';
import { createProfile, deleteProfile, listProfiles } from './api.js';

function mockFetch(status, body) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe('listProfiles', () => {
  it('calls the plain endpoint when there are no filters', async () => {
    const fetchMock = mockFetch(200, []);
    await listProfiles();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/profiles');
  });

  it('adds only the filters that are set', async () => {
    const fetchMock = mockFetch(200, []);
    await listProfiles({ q: 'cse', skill: 'react', availability: 'BUSY' });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/profiles?q=cse&skill=react&availability=BUSY');
  });

  it('treats availability "ALL" as no filter', async () => {
    const fetchMock = mockFetch(200, []);
    await listProfiles({ availability: 'ALL' });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/profiles');
  });
});

describe('errors', () => {
  it('surfaces FastAPI validation errors as a readable message', async () => {
    mockFetch(422, {
      detail: [{ loc: ['body', 'linkedin_url'], msg: 'Value error, must look like https://www.linkedin.com/in/your-name' }],
    });
    await expect(createProfile({ name: 'x' })).rejects.toThrow('linkedin_url: must look like https://www.linkedin.com/in/your-name');
  });

  it('uses a string detail as-is', async () => {
    mockFetch(404, { detail: 'Profile not found' });
    await expect(deleteProfile(99)).rejects.toThrow('Profile not found');
  });
});

describe('deleteProfile', () => {
  it('returns null for 204 No Content', async () => {
    const fetchMock = mockFetch(204, null);
    await expect(deleteProfile(7)).resolves.toBeNull();
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
  });
});
