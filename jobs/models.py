# jobs/models.py - COMPLETE WITH INTERVIEW

from django.db import models
from django.conf import settings
from django.utils import timezone

class Job(models.Model):
    JOB_TYPES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    )
    
    EXPERIENCE_LEVELS = (
        ('entry', 'Entry Level (0-1 years)'),
        ('junior', 'Junior (1-3 years)'),
        ('mid', 'Mid Level (3-5 years)'),
        ('senior', 'Senior (5+ years)'),
        ('lead', 'Lead / Manager'),
    )
    
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField(blank=True)
    
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='full_time')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='entry')
    
    location = models.CharField(max_length=200)
    is_remote = models.BooleanField(default=False)
    
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='NPR')
    
    skills_required = models.JSONField(default=list)
    
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jobs'
    )
    
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_jobs'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # AI Verification
    is_ai_verified = models.BooleanField(default=False)
    ai_verification_score = models.IntegerField(default=0)
    ai_verification_reasons = models.JSONField(default=list)
    ai_verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    @property
    def applications_count(self):
        return self.applications.count()
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_genuine(self):
        return self.is_verified or self.is_ai_verified
    
    @property
    def verification_status(self):
        if self.is_verified:
            return {'status': 'verified', 'message': '✅ Verified by Admin', 'color': '#10B981'}
        elif self.is_ai_verified and self.ai_verification_score >= 80:
            return {'status': 'ai_verified', 'message': f'🤖 AI Verified ({self.ai_verification_score}%)', 'color': '#3B82F6'}
        elif self.ai_verification_score >= 60:
            return {'status': 'suspicious', 'message': f'⚠️ Suspicious - Admin Needs to Verify ({self.ai_verification_score}%)', 'color': '#F59E0B'}
        else:
            return {'status': 'high_risk', 'message': f'🚨 High Suspicion - Admin Review Required ({self.ai_verification_score}%)', 'color': '#EF4444'}
    
    def ai_verify(self):
        score = 0
        reasons = []
        
        if self.company and len(self.company) > 2:
            score += 15
            reasons.append('✅ Company name provided')
        
        if self.title and len(self.title) > 3:
            score += 10
            reasons.append('✅ Job title provided')
        
        if self.description and len(self.description) > 50:
            score += 10
            reasons.append('✅ Detailed description provided')
        
        if self.requirements and len(self.requirements) > 30:
            score += 10
            reasons.append('✅ Requirements listed')
        
        try:
            salary_min = int(self.salary_min) if self.salary_min else 0
            if salary_min > 0:
                score += 10
                reasons.append('✅ Salary mentioned')
        except (ValueError, TypeError):
            pass
        
        if self.skills_required and len(self.skills_required) >= 3:
            score += 15
            reasons.append(f'✅ {len(self.skills_required)} skills listed')
        
        red_flags = []
        text = (self.title + ' ' + self.company + ' ' + self.description + ' ' + self.requirements).lower()
        
        if 'urgent' in text and 'immediate' in text:
            red_flags.append('⚠️ Urgent/Immediate hiring keywords')
        if 'free' in text and 'work' in text:
            red_flags.append('⚠️ "Free work" suspicious')
        if 'no experience' in text and 'senior' in text:
            red_flags.append('⚠️ Contradictory experience requirement')
        if 'unlimited' in text and 'salary' in text:
            red_flags.append('⚠️ Unlimited salary suspicious')
        if 'earn' in text and 'lakh' in text:
            red_flags.append('⚠️ Unrealistic earning claims')
        if 'anyone' in text and 'join' in text:
            red_flags.append('⚠️ "Anyone can join" - no screening')
        
        if not red_flags:
            score += 20
            reasons.append('✅ No red flags detected')
        else:
            score += max(0, 20 - len(red_flags) * 5)
            reasons.extend(red_flags)
        
        self.ai_verification_score = min(score, 100)
        self.ai_verification_reasons = reasons
        
        if self.ai_verification_score >= 80:
            self.is_ai_verified = True
            self.ai_verified_at = timezone.now()
            reasons.append(f'✅ AI Score: {self.ai_verification_score}% - Auto Verified')
        elif self.ai_verification_score >= 60:
            self.is_ai_verified = False
            reasons.append(f'⚠️ AI Score: {self.ai_verification_score}% - Suspicious - Admin Needs to Verify')
        else:
            self.is_ai_verified = False
            reasons.append(f'🚨 AI Score: {self.ai_verification_score}% - High Suspicion - Admin Review Required')
        
        self.save()
        return {
            'score': self.ai_verification_score,
            'verified': self.is_ai_verified,
            'reasons': reasons,
            'status_message': self.verification_status['message'],
        }
    
    class Meta:
        ordering = ['-created_at']


class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('offered', 'Offer Extended'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications'
    )
    
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    recruiter_feedback = models.TextField(blank=True, null=True)
    recruiter_feedback_date = models.DateTimeField(null=True, blank=True)
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.applicant.username} - {self.job.title}"
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'applicant']


# ===== INTERVIEW MODEL =====
class Interview(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    )
    
    application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='interview'
    )
    
    interview_date = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    meeting_link = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_interviews'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Interview for {self.application.job.title} - {self.interview_date}"
    
    @property
    def is_upcoming(self):
        return self.interview_date > timezone.now() and self.status == 'scheduled'
    