# accounts/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password_view, name='reset_password'),
]
