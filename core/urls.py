from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('job-recommendations/', views.job_recommendations, name='job_recommendations'),
]
