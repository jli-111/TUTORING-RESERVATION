import { useEffect, useState } from 'react';
import * as api from '../api/reservations.js';
import * as auth from '../api/auth.js';
import SessionTime from '../components/SessionTime.jsx';
import SlotEditor from './SlotEditor.jsx';

export default function Dashboard({ user, setMode, notify }) {
  const [slots, setSlots] = useState([]);
  const [mine, setMine] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editor, setEditor] = useState(undefined);
  async function load(term = query) {
    const [available, personal] = await Promise.all([
      api.getSlots(term), user ? (user.role === 'tutor' ? api.getTutorSlots() : api.getBookings()) : Promise.resolve([]),
    ]);
    setSlots(available); setMine(personal);
  }
  useEffect(() => {
    let ignore = false;
    setLoading(true);
    Promise.all([api.getSlots(''), user ? (user.role === 'tutor' ? api.getTutorSlots() : api.getBookings()) : Promise.resolve([])])
      .then(([available, personal]) => { if (!ignore) { setSlots(available); setMine(personal); } })
      .catch(error => { if (!ignore) notify(error.message, true); })
      .finally(() => { if (!ignore) setLoading(false); });
    return () => { ignore = true; };
  }, [user?.id, user?.email_verified, user?.tutor_approved]);
  async function mutate(operation, message) {
    setBusy(true);
    try { await operation(); await load(); notify(message); }
    catch (error) { notify(error.message, true); if (error.status === 409) await load().catch(() => {}); }
    finally { setBusy(false); }
  }
  async function search(event) {
    event.preventDefault(); setLoading(true);
    try { await load(); } catch (error) { notify(error.message, true); }
    finally { setLoading(false); }
  }
  const personal = user?.role === 'student' ? mine.filter(b => !b.cancelled_at && new Date(b.slot.ends_at) > new Date()) : mine;
  return <>
    <section className="page-heading"><div><div className="eyebrow">ACADEMIC SUPPORT</div><h1>Tutoring reservations</h1><p className="muted">Find a subject, reserve a session, and manage your schedule.</p></div><div className="time-note">Individual sessions<br /><small>{Intl.DateTimeFormat().resolvedOptions().timeZone}</small></div></section>
    {user && !user.email_verified && <aside className="verification"><div><strong>Verify your email</strong><p>Verification is required before making reservations or publishing lessons.</p></div><button disabled={busy} className="secondary" onClick={() => mutate(auth.resend, 'Check your email for the verification link.')}>Resend verification</button></aside>}
    {user && <section className="panel"><div className="section-heading"><h2>{user.role === 'tutor' ? 'My availability' : 'My lessons'}</h2>{user.role === 'tutor' && user.email_verified && user.tutor_approved && <button onClick={() => setEditor(null)}>Add time slot</button>}</div>
      {user.role === 'tutor' && !user.tutor_approved && <p className="muted">Your tutor account is awaiting administrator approval.</p>}
      {loading ? <p>Loading schedule…</p> : personal.length === 0 ? <p className="muted">No upcoming sessions.</p> : personal.map(item => {
        const slot = user.role === 'student' ? item.slot : item;
        return <div className="lesson-row" key={item.id}><div><strong>{slot.subject}</strong><p><SessionTime slot={slot} /> · {slot.location}</p></div>{user.role === 'student' ? <button disabled={busy || new Date(slot.starts_at) <= new Date()} className="secondary" onClick={() => mutate(() => api.cancelBooking(item.id), 'Reservation cancelled. The slot is available again.')}>Cancel lesson</button> : slot.available ? <button className="secondary" onClick={() => setEditor(slot)}>Edit time</button> : <span className="badge">Booked</span>}</div>;
      })}</section>}
    {editor !== undefined && <SlotEditor key={editor?.id || 'new'} slot={editor} onClose={() => setEditor(undefined)} onSaved={load} notify={notify} />}
    <section><div className="section-heading"><div><h2>Available lessons</h2><p className="muted">Upcoming sessions with approved tutors.</p></div><span className="eyebrow">COURSE DIRECTORY</span></div>
      <form className="search" onSubmit={search}><label htmlFor="subject">Subject</label><div><input id="subject" placeholder="Search by subject, e.g. Mathematics" value={query} onChange={event => setQuery(event.target.value)} /><button disabled={loading}>Search lessons</button></div></form>
      {loading ? <p role="status">Loading lessons…</p> : <div className="cards">{slots.map(slot => <article className="card" key={slot.id}><span className="badge">Individual tutoring</span><h3>{slot.subject}</h3><p className="muted">{slot.tutor_name}</p><p className="session-time"><SessionTime slot={slot} /></p><p>{slot.location}</p>{!user ? <button onClick={() => setMode('login')}>Log in to reserve</button> : user.role === 'student' ? <button disabled={busy || !user.email_verified} onClick={() => mutate(() => api.bookSlot(slot.id), 'Session reserved. Find it in My lessons.')}>{user.email_verified ? 'Reserve session' : 'Verify email to reserve'}</button> : <small>Open for student reservations</small>}</article>)}{slots.length === 0 && <div className="empty"><h3>No available lessons</h3><p>{query ? 'Try another subject.' : 'Sessions will appear when approved tutors publish their schedules.'}</p></div>}</div>}
    </section>
  </>;
}
