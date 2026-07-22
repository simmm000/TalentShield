# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CandidateProfile, RecruiterProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('user_type', 'phone', 'is_verified')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Type', {'fields': ('user_type', 'phone', 'is_verified')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(CandidateProfile)
admin.site.register(RecruiterProfile)
