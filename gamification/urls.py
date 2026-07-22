from django.urls import path
from . import views

urlpatterns = [
    path('challenges/', views.challenges_list, name='challenges_list'),
    path('challenge/<int:challenge_id>/', views.challenge_detail, name='challenge_detail'),
    path('challenge/<int:challenge_id>/submit/', views.submit_challenge, name='submit_challenge'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('gamification/profile/', views.my_profile, name='gamification_profile'),
    path('gamification/skill-recognition/', views.skill_recognition, name='skill_recognition'),
]
