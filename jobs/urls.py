from django.urls import path
from . import views

urlpatterns = [
    path('jobs/', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_detail, name='job_detail'),
    path('job/post/', views.post_job, name='post_job'),
    path('job/<int:job_id>/edit/', views.edit_job, name='edit_job'),
    path('job/<int:job_id>/toggle/', views.toggle_job_status, name='toggle_job_status'),
    path('job/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('job/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('job/<int:job_id>/manage/', views.manage_applications, name='manage_applications'),
    path('api/jobs/stats/', views.job_stats_api, name='job_stats_api'),
    path('download-cv/<int:application_id>/', views.download_cv, name='download_cv'),
    path('view-cv/<int:application_id>/', views.view_cv, name='view_cv'),
    path('withdraw/<int:application_id>/', views.withdraw_application, name='withdraw_application'),
]
