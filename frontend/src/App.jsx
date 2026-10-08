import { useEffect, useState } from 'react';
import * as auth from './api/auth.js';
import AccountPage from './pages/AccountPage.jsx';
import Dashboard from './pages/Dashboard.jsx';

export default function App() {
  const params = new URLSearchParams(location.search);
  const [mode, setMode] = useState(params.has('verify') ? 'verify' : params.has('reset') ? 'reset' : 'dashboard');
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState(null);
  const notify = (text, error = false) => setMessage({ text, error });
  async function bootstrap() {
    try { const result = await auth.getSession(); setUser(result.user); setReady(true); setMessage(null); }
    catch (error) { notify(error.message, true); }
  }
  useEffect(() => { bootstrap(); }, []);
  async function refreshUser(value) {
    setUser(value || (await auth.getSession()).user);
  }
  async function signOut() {
    try { await auth.logout(); setUser(null); setMode('dashboard'); notify('Signed out.'); }
    catch (error) { notify(error.message, true); }
  }
  return <><header><button className="brand" onClick={() => setMode('dashboard')}>Studyroom<small>ACADEMIC TUTORING</small></button><nav><button className="link" onClick={() => setMode('dashboard')}>Course schedule</button>{user ? <><span>{user.username} · {user.role}</span><button className="secondary" onClick={signOut}>Sign out</button></> : <><button className="link" onClick={() => setMode('login')}>Log in</button><button onClick={() => setMode('register')}>Create account</button></>}</nav></header><main>
    {message && <div className={`message ${message.error ? 'error' : ''}`} role={message.error ? 'alert' : 'status'}>{message.text}<button className="link" aria-label="Dismiss message" onClick={() => setMessage(null)}>×</button></div>}
    {!ready ? <section className="panel"><p>Connecting to the reservation service…</p>{message?.error && <button onClick={bootstrap}>Retry connection</button>}</section> : mode === 'dashboard' ? <Dashboard user={user} setMode={setMode} notify={notify} /> : <AccountPage key={mode} mode={mode} setMode={setMode} onAuthenticated={refreshUser} notify={notify} token={params.get(mode === 'verify' ? 'verify' : 'reset')} uid={params.get('uid')} />}
  </main><footer>Studyroom / Academic tutoring<span>One-to-one learning. A clear schedule.</span></footer></>;
}
