import { useState } from 'react';
import Field from '../components/Field.jsx';
import * as auth from '../api/auth.js';

export default function AccountPage({ mode, setMode, onAuthenticated, notify, token, uid }) {
  const [busy, setBusy] = useState(false);
  const title = { login: 'Log in', register: 'Create an account', forgot: 'Reset your password', reset: 'Choose a new password', verify: 'Verify your email' }[mode];
  async function submit(event) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    if (values.confirm !== undefined && values.password !== values.confirm) return notify('Passwords do not match.', true);
    setBusy(true);
    try {
      if (mode === 'login') {
        const result = await auth.login({ username: values.username, password: values.password });
        await onAuthenticated(result.user); setMode('dashboard');
      } else if (mode === 'register') {
        const { confirm, ...body } = values;
        const result = await auth.register(body); notify(result.message); setMode('login');
      } else if (mode === 'forgot') {
        notify((await auth.resetPassword(values.email)).message);
      } else if (mode === 'reset') {
        notify((await auth.confirmPassword({ uid, token, password: values.password })).message);
        history.replaceState({}, '', '/'); setMode('login');
      } else {
        notify((await auth.verify(token)).message);
        history.replaceState({}, '', '/'); await onAuthenticated(); setMode('dashboard');
      }
    } catch (error) { notify(error.message, true); }
    finally { setBusy(false); }
  }
  return <section className="account-layout"><div><div className="eyebrow">STUDYROOM ACCOUNT</div><h1>{title}</h1><p className="muted">Access your lessons and manage your academic schedule.</p><aside>Students can reserve sessions after email verification. Tutors also need administrator approval before publishing availability.</aside></div><form className="panel account-form" onSubmit={submit}>
    {['login', 'register'].includes(mode) && <Field label="Username" name="username" autoComplete="username" required />}
    {['register', 'forgot'].includes(mode) && <Field label="Email" name="email" type="email" autoComplete="email" required />}
    {mode === 'register' && <label className="field">Account type<select name="role"><option value="student">Student</option><option value="tutor">Tutor</option></select></label>}
    {['login', 'register', 'reset'].includes(mode) && <Field label="Password" name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />}
    {['register', 'reset'].includes(mode) && <><Field label="Confirm password" name="confirm" type="password" autoComplete="new-password" required /><small>Use at least 8 characters. Avoid common passwords or personal information.</small></>}
    {mode === 'verify' && <p>Confirm this link to verify ownership of your email address.</p>}
    <button disabled={busy}>{busy ? 'Please wait…' : title}</button>
    {mode === 'login' && <><button type="button" className="link" onClick={() => setMode('forgot')}>Forgot your password?</button><button type="button" className="link" onClick={() => setMode('register')}>Create an account</button></>}
    {mode !== 'login' && <button type="button" className="link" onClick={() => setMode('login')}>Back to login</button>}
  </form></section>;
}
