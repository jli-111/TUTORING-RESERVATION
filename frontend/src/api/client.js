// Shared HTTP transport for JSON requests, session credentials, and CSRF protection.
let csrfToken = '';
export function setCsrfToken(value) { csrfToken = value; }

export async function request(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken;
  const response = await fetch(`/api${path}`, {
    method, headers, credentials: 'same-origin',
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error('The API returned an unexpected response. Check that the backend is running.'); }
  if (!response.ok) {
    const details = data.error?.details;
    const fields = details && typeof details === 'object'
      ? Object.entries(details).filter(([key]) => key !== 'detail')
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`).join(' · ')
      : '';
    const error = new Error(fields || data.error?.message || 'Request failed.');
    error.status = response.status;
    throw error;
  }
  if (data.csrf_token) setCsrfToken(data.csrf_token);
  return data;
}
