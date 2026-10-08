from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Slot, Booking


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Tutoring', {'fields': ('role', 'email_verified', 'tutor_approved')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Tutoring', {'fields': ('email', 'role')}),)
    list_display = ['username', 'email', 'role', 'email_verified', 'tutor_approved']


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


admin.site.register(Slot, ReadOnlyAdmin)
admin.site.register(Booking, ReadOnlyAdmin)
