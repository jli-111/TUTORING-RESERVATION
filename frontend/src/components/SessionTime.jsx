export default function SessionTime({ slot }) {
  return <span>{new Date(slot.starts_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', weekday: 'short' })} · {new Date(slot.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}–{new Date(slot.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>;
}
