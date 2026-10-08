import test from 'node:test';
import assert from 'node:assert/strict';
import { request, setCsrfToken } from './client.js';

test('POST encodes JSON, sends session credentials and CSRF, then adopts rotated token', async () => {
  setCsrfToken('before');
  let sent;
  globalThis.fetch = async (url, options) => {
    sent = { url, ...options };
    return { ok: true, json: async () => ({ csrf_token: 'after', id: 12 }) };
  };
  const value = await request('/bookings/', { method: 'POST', body: { slot_id: 3 } });
  assert.equal(sent.url, '/api/bookings/');
  assert.equal(sent.body, '{"slot_id":3}');
  assert.equal(sent.credentials, 'same-origin');
  assert.equal(sent.headers['X-CSRFToken'], 'before');
  assert.equal(value.id, 12);
  await request('/auth/logout/', { method: 'POST' });
  assert.equal(sent.headers['X-CSRFToken'], 'after');
});

test('a booking conflict is not silently converted into success or an empty list', async () => {
  globalThis.fetch = async () => ({ ok: false, status: 409, json: async () => ({ error: { message: 'Slot taken' } }) });
  await assert.rejects(request('/bookings/', { method: 'POST', body: { slot_id: 1 } }), error => error.status === 409 && error.message === 'Slot taken');
});

test('unexpected server HTML produces a useful connection error', async () => {
  globalThis.fetch = async () => ({ json: async () => { throw new Error('not JSON'); } });
  await assert.rejects(request('/slots/'), /backend is running/);
});
