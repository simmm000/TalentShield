# jobs/admin.py - COMPLETE WITH VERIFICATION

from django.contrib import admin
from django.utils import timezone
from .models import Job, JobApplication

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'job_type', 'is_active', 'is_verified', 'created_at']
    list_filter = ['job_type', 'is_active', 'is_verified', 'is_approved']
    search_fields = ['title', 'company', 'description']
    actions = ['verify_jobs', 'unverify_jobs']
    
    def verify_jobs(self, request, queryset):
        queryset.update(is_verified=True, verified_by=request.user, verified_at=timezone.now())
        self.message_user(request, f"{queryset.count()} jobs verified successfully!")
    verify_jobs.short_description = "✅ Verify selected jobs"
    
    def unverify_jobs(self, request, queryset):
        queryset.update(is_verified=False, verified_by=None, verified_at=None)
        self.message_user(request, f"{queryset.count()} jobs unverified!")
    unverify_jobs.short_description = "❌ Unverify selected jobs"

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'job', 'status', 'applied_at']
    list_filter = ['status']
    search_fields = ['applicant__username', 'job__title']
    