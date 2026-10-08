from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from urllib.parse import urlparse, parse_qs
from django.core import mail, signing
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
from .models import User, Slot, Booking
from .services import book, cancel, save_slot
from .errors import Conflict

PASSWORD = 'Testing-Passphrase-287!'


def fixtures():
    tutor = User.objects.create_user('tutor', email='tutor@example.com', password=PASSWORD,
        role='tutor', email_verified=True, tutor_approved=True)
    student = User.objects.create_user('student', email='student@example.com', password=PASSWORD,
        role='student', email_verified=True)
    other = User.objects.create_user('other', email='other@example.com', password=PASSWORD,
        role='student', email_verified=True)
    start = timezone.now() + timedelta(days=3)
    slot = Slot.objects.create(tutor=tutor, subject='Mathematics', starts_at=start, ends_at=start+timedelta(hours=1))
    return tutor, student, other, slot


class ApiTests(TestCase):
    def setUp(self):
        self.tutor, self.student, self.other, self.slot = fixtures()
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/auth/session/').data['csrf_token']

    def post(self, path, body=None, method='post'):
        return getattr(self.client, method)(path, body or {}, format='json', HTTP_X_CSRFTOKEN=self.csrf)

    def sign_in(self, user=None):
        response = self.post('/api/auth/login/', {'username': (user or self.student).username, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.csrf = response.data['csrf_token']
        return response

    def test_mysql_is_the_actual_test_engine(self):
        self.assertEqual(connection.vendor, 'mysql')
        with connection.cursor() as cursor:
            cursor.execute("SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='reservations_booking'")
            self.assertEqual(cursor.fetchone()[0], 'InnoDB')

    def test_public_slots_return_json_not_html(self):
        response = self.client.get('/api/slots/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.data[0]['id'], self.slot.pk)
        self.assertNotIn('password', response.data[0])

    def test_search(self):
        self.assertEqual(len(self.client.get('/api/slots/?q=Physics').data), 0)
        self.assertEqual(len(self.client.get('/api/slots/?q=Math').data), 1)

    def test_unauthenticated_write_denied(self):
        self.assertEqual(self.post('/api/bookings/', {'slot_id': self.slot.pk}).status_code, 403)

    def test_anonymous_login_requires_csrf(self):
        response = self.client.post('/api/auth/login/', {'username': 'student', 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_registration_hash_and_verification(self):
        response = self.post('/api/auth/register/', {'username':'new', 'email':'NEW@example.com', 'role':'student', 'password':PASSWORD, 'tutor_approved':True})
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username='new')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.email_verified)
        self.assertFalse(user.tutor_approved)
        self.assertEqual(user.email, 'new@example.com')
        query = parse_qs(urlparse(mail.outbox[-1].body.splitlines()[-1]).query)
        response = self.post('/api/auth/verify/', {'token':query['verify'][0]})
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_invalid_and_expired_verification(self):
        self.assertEqual(self.post('/api/auth/verify/', {'token':'fake'}).status_code, 400)
        from unittest.mock import patch
        with patch('django.core.signing.time.time', return_value=1):
            token = signing.dumps({'id':self.student.pk, 'email':self.student.email}, salt='email-verification')
        self.assertEqual(self.post('/api/auth/verify/', {'token':token}).status_code, 400)

    def test_duplicate_email_and_weak_password(self):
        self.assertEqual(self.post('/api/auth/register/', {'username':'new', 'email':'STUDENT@example.com', 'role':'student', 'password':PASSWORD}).status_code, 400)
        self.assertEqual(self.post('/api/auth/register/', {'username':'new', 'email':'new@example.com', 'role':'student', 'password':'123'}).status_code, 400)

    def test_login_wrong_password_and_logout(self):
        self.assertEqual(self.post('/api/auth/login/', {'username':'student', 'password':'wrong'}).status_code, 403)
        response = self.sign_in()
        self.assertNotIn('password', response.data['user'])
        self.assertEqual(self.post('/api/auth/logout/').status_code, 200)
        self.assertIsNone(self.client.get('/api/auth/session/').data['user'])

    def test_authenticated_write_requires_csrf(self):
        self.sign_in()
        response = self.client.post('/api/bookings/', {'slot_id':self.slot.pk}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_book_cancel_rebook(self):
        self.sign_in()
        response = self.post('/api/bookings/', {'slot_id':self.slot.pk, 'student_id':self.other.pk})
        self.assertEqual(response.status_code, 201)
        booking = Booking.objects.get(pk=response.data['id'])
        self.assertEqual(booking.student_id, self.student.pk)
        self.assertEqual(booking.active_slot_key, self.slot.pk)
        self.assertEqual(len(self.client.get('/api/slots/').data), 0)
        self.assertEqual(self.post(f'/api/bookings/{booking.pk}/cancel/').status_code, 200)
        booking.refresh_from_db()
        self.assertIsNone(booking.active_slot_key)
        self.assertEqual(len(self.client.get('/api/slots/').data), 1)
        book(self.other, self.slot.pk)
        self.assertEqual(Booking.objects.count(), 2)

    def test_double_booking_returns_409(self):
        book(self.other, self.slot.pk)
        self.sign_in()
        self.assertEqual(self.post('/api/bookings/', {'slot_id':self.slot.pk}).status_code, 409)

    def test_unique_generated_column_rejects_direct_duplicate(self):
        Booking.objects.create(student=self.student, slot=self.slot)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(student=self.other, slot=self.slot)

    def test_multiple_cancelled_rows_allowed(self):
        for user in [self.student, self.other, self.student]:
            cancel(user, book(user, self.slot.pk).pk)
        self.assertEqual(Booking.objects.count(), 3)
        self.assertEqual(Booking.objects.filter(active_slot_key__isnull=False).count(), 0)

    def test_cannot_cancel_another_student(self):
        booking = book(self.other, self.slot.pk)
        self.sign_in()
        self.assertEqual(self.post(f'/api/bookings/{booking.pk}/cancel/').status_code, 404)

    def test_unverified_student_cannot_book(self):
        self.student.email_verified = False; self.student.save()
        self.sign_in()
        self.assertEqual(self.post('/api/bookings/', {'slot_id':self.slot.pk}).status_code, 403)

    def test_tutor_cannot_book(self):
        self.sign_in(self.tutor)
        self.assertEqual(self.post('/api/bookings/', {'slot_id':self.slot.pk}).status_code, 403)

    def test_tutor_edit_and_booked_slot_protection(self):
        self.sign_in(self.tutor)
        data = {'subject':'Algebra', 'location':'Online', 'starts_at':(self.slot.starts_at+timedelta(hours=2)).isoformat(), 'ends_at':(self.slot.ends_at+timedelta(hours=2)).isoformat()}
        self.assertEqual(self.post(f'/api/tutor/slots/{self.slot.pk}/', data, 'put').status_code, 200)
        book(self.student, self.slot.pk)
        self.assertEqual(self.post(f'/api/tutor/slots/{self.slot.pk}/', data, 'put').status_code, 409)

    def test_student_cannot_create_slots(self):
        self.sign_in()
        self.assertEqual(self.post('/api/tutor/slots/', {}).status_code, 403)

    def test_unapproved_tutor_and_other_tutor(self):
        self.other.role='tutor'; self.other.email_verified=True; self.other.save()
        self.sign_in(self.other)
        data = {'subject':'Physics', 'location':'Online', 'starts_at':self.slot.starts_at.isoformat(), 'ends_at':self.slot.ends_at.isoformat()}
        self.assertEqual(self.post('/api/tutor/slots/', data).status_code, 403)
        self.other.tutor_approved=True; self.other.save()
        self.assertEqual(self.post(f'/api/tutor/slots/{self.slot.pk}/', data, 'put').status_code, 404)

    def test_invalid_time_and_overlap(self):
        self.sign_in(self.tutor)
        data = {'subject':'Physics', 'location':'Online', 'starts_at':self.slot.starts_at.isoformat(), 'ends_at':self.slot.ends_at.isoformat()}
        self.assertEqual(self.post('/api/tutor/slots/', data).status_code, 409)
        data['ends_at'] = (self.slot.starts_at-timedelta(hours=1)).isoformat()
        self.assertEqual(self.post('/api/tutor/slots/', data).status_code, 400)

    def test_password_reset_and_token_reuse(self):
        self.assertEqual(self.post('/api/auth/password-reset/', {'email':self.student.email}).status_code, 200)
        query = parse_qs(urlparse(mail.outbox[-1].body.splitlines()[-1]).query)
        data = {'uid':query['uid'][0], 'token':query['reset'][0], 'password':'New-Strong-Passphrase-872!'}
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', data).status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password(data['password']))
        self.assertEqual(self.post('/api/auth/password-reset/confirm/', data).status_code, 400)

    def test_unknown_reset_email_generic_response(self):
        unknown = self.post('/api/auth/password-reset/', {'email':'missing@example.com'})
        known = self.post('/api/auth/password-reset/', {'email':self.student.email})
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_json_fields_do_not_produce_500(self):
        self.sign_in()
        for value in ['x', -1, None]:
            self.assertEqual(self.post('/api/bookings/', {'slot_id':value}).status_code, 400)


class RaceTests(TransactionTestCase):
    def setUp(self):
        self.tutor, self.student, self.other, self.slot = fixtures()

    def race(self, operations):
        barrier = Barrier(2)
        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    operation()
                    return 'success'
                except Conflict:
                    return 'conflict'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, operations))

    def test_two_students_one_slot(self):
        results = self.race([lambda: book(self.student, self.slot.pk), lambda: book(self.other, self.slot.pk)])
        self.assertCountEqual(results, ['success','conflict'])
        self.assertEqual(Booking.objects.filter(cancelled_at__isnull=True).count(), 1)

    def test_one_student_two_overlapping_slots(self):
        tutor2 = User.objects.create_user('tutor2', email='t2@example.com', role='tutor', email_verified=True, tutor_approved=True)
        slot2 = Slot.objects.create(tutor=tutor2, subject='Physics', starts_at=self.slot.starts_at, ends_at=self.slot.ends_at)
        results = self.race([lambda: book(self.student, self.slot.pk), lambda: book(self.student, slot2.pk)])
        self.assertCountEqual(results, ['success','conflict'])
        self.assertEqual(Booking.objects.filter(student=self.student, cancelled_at__isnull=True).count(), 1)

    def test_two_overlapping_tutor_creates(self):
        data = {'subject':'New', 'location':'Online', 'starts_at':self.slot.starts_at+timedelta(days=1), 'ends_at':self.slot.ends_at+timedelta(days=1)}
        results = self.race([lambda: save_slot(self.tutor, data), lambda: save_slot(self.tutor, data)])
        self.assertCountEqual(results, ['success','conflict'])

    def test_cancellation_and_rebooking_serialize(self):
        original = book(self.student, self.slot.pk)
        results = self.race([lambda: cancel(self.student, original.pk), lambda: book(self.other, self.slot.pk)])
        self.assertEqual(results[0], 'success')
        self.assertIn(results[1], ['success', 'conflict'])
        self.assertLessEqual(Booking.objects.filter(cancelled_at__isnull=True).count(), 1)
        original.refresh_from_db()
        self.assertIsNotNone(original.cancelled_at)

    def test_booking_and_edit_serialize(self):
        data = {'subject':'Updated', 'location':'Online', 'starts_at':self.slot.starts_at+timedelta(hours=2), 'ends_at':self.slot.ends_at+timedelta(hours=2)}
        results = self.race([lambda: book(self.student, self.slot.pk), lambda: save_slot(self.tutor, data, self.slot.pk)])
        self.assertEqual(results[0], 'success')
        self.assertIn(results[1], ['success', 'conflict'])
        self.assertEqual(Booking.objects.filter(cancelled_at__isnull=True).count(), 1)
