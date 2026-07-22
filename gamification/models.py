# gamification/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone

class Challenge(models.Model):
    DIFFICULTY_LEVELS = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    )
    
    CATEGORIES = (
        ('network_security', 'Network Security'),
        ('web_security', 'Web Security'),
        ('cryptography', 'Cryptography'),
        ('incident_response', 'Incident Response'),
        ('threat_analysis', 'Threat Analysis'),
        ('ethical_hacking', 'Ethical Hacking'),
        ('forensics', 'Digital Forensics'),
        ('compliance', 'Compliance & Risk'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORIES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)
    
    question = models.TextField()
    scenario = models.TextField(blank=True)
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField()
    answer_type = models.CharField(max_length=20, default='text')
    
    hints = models.JSONField(default=list, blank=True)
    
    points = models.IntegerField(default=10)
    time_limit_seconds = models.IntegerField(default=300)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} ({self.difficulty})"
    
    class Meta:
        ordering = ['difficulty', 'category']


class ChallengeAttempt(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    )
    
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenge_attempts'
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    submitted_answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    time_taken_seconds = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.candidate.username} - {self.challenge.title} - {'PASS' if self.is_correct else 'FAIL'}"
    
    class Meta:
        ordering = ['-completed_at']


class Achievement(models.Model):
    ACHIEVEMENT_TYPES = (
        ('challenge_master', 'Challenge Master'),
        ('certification_verified', 'Certification Verified'),
        ('fraud_free', 'Fraud-Free Profile'),
        ('top_performer', 'Top Performer'),
        ('skill_expert', 'Skill Expert'),
        ('quick_learner', 'Quick Learner'),
        ('streak_master', 'Streak Master'),
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50, default='🏆')
    points_bonus = models.IntegerField(default=0)
    requirements = models.JSONField(default=dict)
    
    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='users'
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.candidate.username} - {self.achievement.name}"
    
    class Meta:
        unique_together = ['candidate', 'achievement']


class GamificationProfile(models.Model):
    candidate = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gamification_profile'
    )
    
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    experience_points = models.IntegerField(default=0)
    
    challenges_attempted = models.IntegerField(default=0)
    challenges_passed = models.IntegerField(default=0)
    challenges_failed = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    
    current_streak_days = models.IntegerField(default=0)
    longest_streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    badges = models.JSONField(default=list)
    badges_count = models.IntegerField(default=0)
    
    # ===== CV BOOST =====
    cv_boost_percentage = models.IntegerField(default=0)  # 0-50%
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.candidate.username} - Level {self.level} ({self.total_points} pts) - Boost: {self.cv_boost_percentage}%"
    
    def add_points(self, points):
        """Add points and update CV boost"""
        self.total_points += points
        self.experience_points += points
        
        while self.experience_points >= self.level * 100:
            self.experience_points -= self.level * 100
            self.level += 1
        
        # Update CV boost after adding points
        self.update_cv_boost()
        self.save()
    
    def update_cv_boost(self):
        """Update CV boost percentage based on challenges passed"""
        passed = self.challenges_passed
        
        if passed >= 20:
            self.cv_boost_percentage = 50
        elif passed >= 15:
            self.cv_boost_percentage = 40
        elif passed >= 10:
            self.cv_boost_percentage = 30
        elif passed >= 5:
            self.cv_boost_percentage = 20
        elif passed >= 3:
            self.cv_boost_percentage = 10
        else:
            self.cv_boost_percentage = 0
        
        return self.cv_boost_percentage
    
    class Meta:
        ordering = ['-total_points']
        