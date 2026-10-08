import { useState } from 'react';
import Field from '../components/Field.jsx';
import { saveSlot } from '../api/reservations.js';

function localInput(value) {
  if (!value) return '';
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
export default function SlotEditor({ slot, onClose, onSaved, notify }) {
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true);
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      values.starts_at = new Date(values.starts_at).toISOString();
      values.ends_at = new Date(values.ends_at).toISOString();
      await saveSlot(values, slot?.id); await onSaved(); onClose(); notify('Availability saved.');
    } catch (error) { notify(error.message, true); }
    finally { setBusy(false); }
  }
  return <section className="panel"><h2>{slot ? 'Edit time slot' : 'Add time slot'}</h2><p className="muted">Enter times in your local timezone: {Intl.DateTimeFormat().resolvedOptions().timeZone}. Booked slots cannot be changed.</p><form onSubmit={submit} className="editor">
    <Field label="Subject" name="subject" defaultValue={slot?.subject} maxLength={120} required />
    <Field label="Location" name="location" defaultValue={slot?.location || 'Online'} maxLength={200} required />
    <Field label="Starts at" name="starts_at" type="datetime-local" defaultValue={localInput(slot?.starts_at)} required />
    <Field label="Ends at" name="ends_at" type="datetime-local" defaultValue={localInput(slot?.ends_at)} required />
    <div className="actions"><button disabled={busy}>{busy ? 'Saving…' : 'Save availability'}</button><button type="button" className="secondary" onClick={onClose}>Cancel</button></div>
  </form></section>;
}
