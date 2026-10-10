import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  createProfile,
  deleteProfile,
  listProfiles,
  me,
  removeConnection,
  resumeUrl,
  sendRequest,
  uploadResume,
} from './api.js';

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

describe('accounts', () => {
  it('me() returns null when logged out instead of throwing', async () => {
    mockFetch(401, { detail: 'Log in first' });
    await expect(me()).resolves.toBeNull();
  });

  it('me() still throws for real errors', async () => {
    mockFetch(500, { detail: 'boom' });
    await expect(me()).rejects.toThrow('boom');
  });

  it('errors carry the HTTP status', async () => {
    mockFetch(403, { detail: 'You can only change your own profile' });
    const err = await createProfile({ name: 'x' }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(403);
  });
});

describe('requests', () => {
  it('sends JSON with a JSON content type and same-origin cookies', async () => {
    const fetchMock = mockFetch(201, {});
    await sendRequest(7);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/connections/requests');
    expect(options.method).toBe('POST');
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual({ user_id: 7 });
    expect(options.credentials).toBe('same-origin');
  });

  it('uploads a resume as multipart form data (no JSON header)', async () => {
    const fetchMock = mockFetch(200, { filename: 'cv.pdf' });
    const file = new Blob(['%PDF-1.7'], { type: 'application/pdf' });
    await uploadResume(3, file);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe(resumeUrl(3));
    expect(options.method).toBe('PUT');
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers).toBeUndefined();
  });

  it('removes a connection by user id', async () => {
    const fetchMock = mockFetch(204, null);
    await removeConnection(12);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/connections/12');
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
  });
});
