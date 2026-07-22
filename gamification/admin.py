# gamification/admin.py

from django.contrib import admin
from .models import Challenge, ChallengeAttempt, Achievement, UserAchievement, GamificationProfile

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'category', 'points', 'is_active']
    list_filter = ['difficulty', 'category', 'is_active']
    search_fields = ['title', 'description']

@admin.register(ChallengeAttempt)
class ChallengeAttemptAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'challenge', 'is_correct', 'score', 'completed_at']
    list_filter = ['is_correct', 'status']
    search_fields = ['candidate__username']

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'points_bonus']
    list_filter = ['type']

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'achievement', 'earned_at']
    search_fields = ['candidate__username']

@admin.register(GamificationProfile)
class GamificationProfileAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'total_points', 'level', 'challenges_passed', 'badges_count']
    search_fields = ['candidate__username']
    