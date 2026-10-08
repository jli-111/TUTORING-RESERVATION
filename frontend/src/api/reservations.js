// API operations for lesson availability and student reservations.
import { request } from './client.js';
export const getSlots = query => request(`/slots/?q=${encodeURIComponent(query || '')}`);
export const getBookings = () => request('/bookings/');
export const bookSlot = slotId => request('/bookings/', { method: 'POST', body: { slot_id: slotId } });
export const cancelBooking = id => request(`/bookings/${id}/cancel/`, { method: 'POST' });
export const getTutorSlots = () => request('/tutor/slots/');
export const saveSlot = (slot, id) => request(id ? `/tutor/slots/${id}/` : '/tutor/slots/', { method: id ? 'PUT' : 'POST', body: slot });
