import { request } from './client.js';
export const getSession = () => request('/auth/session/');
export const register = body => request('/auth/register/', { method: 'POST', body });
export const login = body => request('/auth/login/', { method: 'POST', body });
export const logout = () => request('/auth/logout/', { method: 'POST' });
export const verify = token => request('/auth/verify/', { method: 'POST', body: { token } });
export const resend = () => request('/auth/resend/', { method: 'POST' });
export const resetPassword = email => request('/auth/password-reset/', { method: 'POST', body: { email } });
export const confirmPassword = body => request('/auth/password-reset/confirm/', { method: 'POST', body });
