# cv_processor/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('api/cv/upload-analyze/', views.CVUploadAndAnalyzeView.as_view(), name='cv-upload-analyze'),
]
