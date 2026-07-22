# cv_processor/admin.py

from django.contrib import admin
from .models import CVAnalysis

@admin.register(CVAnalysis)
class CVAnalysisAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'fraud_score_percentage', 'fraud_risk_level', 'created_at']
    list_filter = ['fraud_risk_level', 'created_at']
    search_fields = ['candidate__username', 'candidate__email']
    readonly_fields = ['created_at', 'updated_at']
    