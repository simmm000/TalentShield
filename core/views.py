# core/views.py - UPDATED RECRUITER STATS

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from jobs.models import Job, JobApplication
from cv_processor.models import CVAnalysis


def home(request):
    context = {
        'total_cvs_analyzed': CVAnalysis.objects.count(),
        'total_jobs': Job.objects.count(),
        'total_applications': JobApplication.objects.count(),
        'total_users': User.objects.count(),
        'total_candidates': User.objects.filter(user_type='candidate').count(),
        'total_recruiters': User.objects.filter(user_type='recruiter').count(),
    }
    return render(request, 'core/home.html', context)


@login_required
def dashboard(request):
    user_type = request.user.user_type
    
    if user_type == 'candidate':
        fraud_data = CVAnalysis.objects.filter(candidate=request.user).first()
        
        fraud_score = 'N/A'
        fraud_risk = 'Not Analyzed'
        fraud_factors = []
        
        if fraud_data:
            fraud_score = fraud_data.fraud_score_percentage
            fraud_risk = fraud_data.fraud_risk_level
            if fraud_data.fraud_details:
                fraud_factors = fraud_data.fraud_details.get('fraud_factors', [])
        
        return render(request, 'core/candidate_dashboard.html', {
            'fraud_score': fraud_score,
            'fraud_risk': fraud_risk,
            'fraud_factors': fraud_factors,
        })
    
    elif user_type == 'recruiter':
        jobs = Job.objects.filter(posted_by=request.user)
        
        # ✅ EXCLUDE WITHDRAWN APPLICATIONS
        active_applications = JobApplication.objects.filter(
            job__in=jobs
        ).exclude(status='withdrawn')
        
        # ✅ UNIQUE candidates
        active_candidates = active_applications.values('applicant').distinct().count()
        
        filtered_data = []
        for app in active_applications:
            try:
                cv_analysis = CVAnalysis.objects.filter(
                    candidate=app.applicant
                ).first()
                
                if cv_analysis:
                    filtered_data.append({
                        'applicant': app.applicant,
                        'job': app.job,
                        'fraud_score': cv_analysis.fraud_score_percentage,
                        'risk_level': cv_analysis.fraud_risk_level,
                        'status': app.status,
                    })
                else:
                    filtered_data.append({
                        'applicant': app.applicant,
                        'job': app.job,
                        'fraud_score': 0,
                        'risk_level': 'Not Analyzed',
                        'status': app.status,
                    })
            except:
                continue
        
        context = {
            'applications': filtered_data,
            'total_jobs': jobs.count(),
            'total_applications': active_applications.count(),  # ✅ Excludes withdrawn
            'total_candidates': active_candidates,
        }
        return render(request, 'core/recruiter_dashboard.html', context)
    
    elif user_type == 'admin':
        context = {
            'total_users': User.objects.count(),
            'total_candidates': User.objects.filter(user_type='candidate').count(),
            'total_recruiters': User.objects.filter(user_type='recruiter').count(),
            'total_jobs': Job.objects.count(),
            'total_applications': JobApplication.objects.count(),
            'total_cv_analyses': CVAnalysis.objects.count(),
            'high_risk_cvs': CVAnalysis.objects.filter(fraud_risk_level='High').count(),
            'medium_risk_cvs': CVAnalysis.objects.filter(fraud_risk_level='Medium').count(),
            'low_risk_cvs': CVAnalysis.objects.filter(fraud_risk_level='Low').count(),
            'users': User.objects.all().order_by('-date_joined')[:10],
        }
        return render(request, 'core/admin_dashboard.html', context)
    
    return redirect('home')


@login_required
def job_recommendations(request):
    """AI-based job recommendations for candidates"""
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can view recommendations.')
        return redirect('dashboard')
    
    try:
        profile = request.user.candidate_profile
        candidate_skills = set(profile.skills)
        
        if not candidate_skills:
            messages.info(request, 'Upload your CV to get personalized job recommendations.')
            return render(request, 'core/job_recommendations.html', {
                'recommendations': [],
                'candidate_skills': [],
                'total_recommendations': 0,
            })
        
        jobs = Job.objects.filter(is_active=True)
        
        recommendations = []
        for job in jobs:
            job_skills = set(job.skills_required)
            if job_skills:
                matched = candidate_skills & job_skills
                match_percentage = int((len(matched) / len(job_skills)) * 100) if job_skills else 0
                
                if match_percentage >= 30:
                    recommendations.append({
                        'job': job,
                        'match': match_percentage,
                        'matched_skills': list(matched),
                        'total_skills': len(job_skills),
                    })
        
        recommendations.sort(key=lambda x: x['match'], reverse=True)
        
        return render(request, 'core/job_recommendations.html', {
            'recommendations': recommendations[:10],
            'total_recommendations': len(recommendations),
            'candidate_skills': list(candidate_skills),
        })
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return render(request, 'core/job_recommendations.html', {
            'recommendations': [],
            'candidate_skills': [],
            'total_recommendations': 0,
        })
    