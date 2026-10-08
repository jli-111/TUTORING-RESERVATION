from django.contrib import admin
from django.urls import path
from reservations import auth_views as auth, views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/session/', auth.session),
    path('api/auth/register/', auth.register),
    path('api/auth/login/', auth.sign_in),
    path('api/auth/logout/', auth.sign_out),
    path('api/auth/verify/', auth.verify_email),
    path('api/auth/resend/', auth.resend),
    path('api/auth/password-reset/', auth.password_reset),
    path('api/auth/password-reset/confirm/', auth.password_confirm),
    path('api/slots/', views.slots),
    path('api/tutor/slots/', views.tutor_slots),
    path('api/tutor/slots/<int:pk>/', views.tutor_slot_detail),
    path('api/bookings/', views.bookings),
    path('api/bookings/<int:pk>/cancel/', views.booking_cancel),
]
