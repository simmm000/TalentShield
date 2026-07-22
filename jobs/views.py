# jobs/views.py - COMPLETE WITH WITHDRAW APPLICATION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.utils import timezone
from .models import Job, JobApplication
from accounts.models import CandidateProfile
import os


@login_required
def job_list(request):
    """Display all active jobs"""
    jobs = Job.objects.filter(is_active=True)
    
    job_type = request.GET.get('type')
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    experience = request.GET.get('experience')
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    search = request.GET.get('search')
    if search:
        jobs = jobs.filter(
            models.Q(title__icontains=search) |
            models.Q(company__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(location__icontains=search)
        )
    
    return render(request, 'jobs/job_list.html', {
        'jobs': jobs,
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def job_detail(request, job_id):
    """Display job details"""
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    has_applied = False
    if request.user.user_type == 'candidate':
        has_applied = JobApplication.objects.filter(
            job=job,
            applicant=request.user
        ).exists()
    
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
    })


@login_required
def post_job(request):
    """Post a new job (Recruiter only)"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can post jobs.')
        return redirect('job_list')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        company = request.POST.get('company')
        description = request.POST.get('description')
        requirements = request.POST.get('requirements')
        responsibilities = request.POST.get('responsibilities', '')
        job_type = request.POST.get('job_type')
        experience_level = request.POST.get('experience_level')
        location = request.POST.get('location')
        is_remote = request.POST.get('is_remote') == 'on'
        salary_min = request.POST.get('salary_min')
        salary_max = request.POST.get('salary_max')
        skills = request.POST.get('skills', '').split(',')
        skills = [s.strip() for s in skills if s.strip()]
        
        job = Job.objects.create(
            title=title,
            company=company,
            description=description,
            requirements=requirements,
            responsibilities=responsibilities,
            job_type=job_type,
            experience_level=experience_level,
            location=location,
            is_remote=is_remote,
            salary_min=salary_min or None,
            salary_max=salary_max or None,
            skills_required=skills,
            posted_by=request.user,
            is_approved=True,
        )
        
        messages.success(request, 'Job posted successfully!')
        return redirect('my_jobs')
    
    return render(request, 'jobs/post_job.html', {
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def my_jobs(request):
    """Show recruiter's posted jobs"""
    if request.user.user_type != 'recruiter':
        return redirect('job_list')
    
    jobs = Job.objects.filter(posted_by=request.user)
    return render(request, 'jobs/my_jobs.html', {
        'jobs': jobs,
    })


@login_required
def apply_job(request, job_id):
    """Apply to a job (Candidate only)"""
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can apply.')
        return redirect('job_detail', job_id=job_id)
    
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied to this job.')
        return redirect('job_detail', job_id=job_id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')
        
        application = JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
            status='pending'
        )
        
        messages.success(request, 'Application submitted successfully!')
        return redirect('my_applications')
    
    return render(request, 'jobs/apply_job.html', {
        'job': job,
    })


@login_required
def my_applications(request):
    """Show candidate's applications with feedback"""
    if request.user.user_type != 'candidate':
        return redirect('job_list')
    
    applications = JobApplication.objects.filter(
        applicant=request.user
    ).select_related('job')
    
    return render(request, 'jobs/my_applications.html', {
        'applications': applications,
    })


@login_required
def manage_applications(request, job_id):
    """Recruiter manages applications with feedback"""
    if request.user.user_type != 'recruiter':
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    applications = JobApplication.objects.filter(job=job)
    
    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        new_status = request.POST.get('status')
        feedback = request.POST.get('feedback', '')
        
        application = get_object_or_404(JobApplication, id=application_id, job=job)
        application.status = new_status
        application.recruiter_feedback = feedback
        application.recruiter_feedback_date = timezone.now()
        application.save()
        messages.success(request, 'Application updated successfully!')
        
        return redirect('manage_applications', job_id=job_id)
    
    return render(request, 'jobs/manage_applications.html', {
        'job': job,
        'applications': applications,
        'status_choices': JobApplication.STATUS_CHOICES,
    })


@login_required
def job_stats_api(request):
    """API endpoint for recruiter job stats"""
    if request.user.user_type != 'recruiter':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    jobs = Job.objects.filter(posted_by=request.user)
    total_jobs = jobs.count()
    total_applications = JobApplication.objects.filter(job__in=jobs).count()
    
    return JsonResponse({
        'total_jobs': total_jobs,
        'total_applications': total_applications,
    })


@login_required
def edit_job(request, job_id):
    """Edit a job posting"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can edit jobs.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    
    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.company = request.POST.get('company')
        job.description = request.POST.get('description')
        job.requirements = request.POST.get('requirements')
        job.responsibilities = request.POST.get('responsibilities', '')
        job.job_type = request.POST.get('job_type')
        job.experience_level = request.POST.get('experience_level')
        job.location = request.POST.get('location')
        job.is_remote = request.POST.get('is_remote') == 'on'
        job.salary_min = request.POST.get('salary_min') or None
        job.salary_max = request.POST.get('salary_max') or None
        skills = request.POST.get('skills', '').split(',')
        job.skills_required = [s.strip() for s in skills if s.strip()]
        job.save()
        
        messages.success(request, 'Job updated successfully!')
        return redirect('my_jobs')
    
    return render(request, 'jobs/edit_job.html', {
        'job': job,
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def toggle_job_status(request, job_id):
    """Toggle job active/inactive status"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can change job status.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    job.is_active = not job.is_active
    job.save()
    
    status = 'activated' if job.is_active else 'deactivated'
    messages.success(request, f'Job {status} successfully!')
    return redirect('my_jobs')


@login_required
def delete_job(request, job_id):
    """Delete a job posting"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can delete jobs.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    
    if request.GET.get('confirm') == 'yes':
        job_title = job.title
        job.delete()
        messages.success(request, f'Job "{job_title}" deleted successfully!')
        return redirect('my_jobs')
    
    return render(request, 'jobs/delete_job.html', {
        'job': job,
    })


@login_required
def view_cv(request, application_id):
    """Recruiter views candidate's CV"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can view CVs.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id)
    
    if application.job.posted_by != request.user:
        messages.error(request, 'You are not authorized to view this CV.')
        return redirect('job_list')
    
    try:
        profile = CandidateProfile.objects.get(user=application.applicant)
        
        if not profile.cv_file:
            messages.error(request, 'Candidate has not uploaded a CV yet.')
            return redirect('manage_applications', job_id=application.job.id)
        
        # Direct redirect to file
        return redirect(profile.cv_file.url)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('manage_applications', job_id=application.job.id)


@login_required
def download_cv(request, application_id):
    """Recruiter downloads candidate's CV"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can download CVs.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id)
    
    if application.job.posted_by != request.user:
        messages.error(request, 'You are not authorized to download this CV.')
        return redirect('job_list')
    
    try:
        profile = CandidateProfile.objects.get(user=application.applicant)
        
        if not profile.cv_file:
            messages.error(request, 'Candidate has not uploaded a CV yet.')
            return redirect('manage_applications', job_id=application.job.id)
        
        # Direct redirect to file
        return redirect(profile.cv_file.url)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('manage_applications', job_id=application.job.id)


# ============================================================
# ===== WITHDRAW APPLICATION =====
# ============================================================

@login_required
def withdraw_application(request, application_id):
    """Candidate withdraws their job application"""
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can withdraw applications.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id, applicant=request.user)
    
    # Check if already withdrawn
    if application.status == 'withdrawn':
        messages.warning(request, 'Application already withdrawn.')
        return redirect('my_applications')
    
    # Check if application is already hired or rejected
    if application.status in ['hired', 'rejected']:
        messages.error(request, f'Cannot withdraw {application.status} application.')
        return redirect('my_applications')
    
    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()
        messages.success(request, f'Application for "{application.job.title}" withdrawn successfully!')
        return redirect('my_applications')
    
    return render(request, 'jobs/withdraw_confirm.html', {
        'application': application,
    })
# jobs/views.py - COMPLETE WITH ALL FUNCTIONS

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.utils import timezone
from .models import Job, JobApplication
from accounts.models import CandidateProfile
from cv_processor.models import CVAnalysis
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    
    job_type = request.GET.get('type')
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    experience = request.GET.get('experience')
    if experience:
        jobs = jobs.filter(experience_level=experience)
    
    search = request.GET.get('search')
    if search:
        jobs = jobs.filter(
            models.Q(title__icontains=search) |
            models.Q(company__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(location__icontains=search)
        )
    
    genuine = request.GET.get('genuine')
    if genuine == 'verified':
        jobs = jobs.filter(is_verified=True)
    elif genuine == 'unverified':
        jobs = jobs.filter(is_verified=False)
    
    return render(request, 'jobs/job_list.html', {
        'jobs': jobs,
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    has_applied = False
    if request.user.user_type == 'candidate':
        has_applied = JobApplication.objects.filter(
            job=job,
            applicant=request.user
        ).exists()
    
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
    })


@login_required
def post_job(request):
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can post jobs.')
        return redirect('job_list')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        company = request.POST.get('company')
        description = request.POST.get('description')
        requirements = request.POST.get('requirements')
        responsibilities = request.POST.get('responsibilities', '')
        job_type = request.POST.get('job_type')
        experience_level = request.POST.get('experience_level')
        location = request.POST.get('location')
        is_remote = request.POST.get('is_remote') == 'on'
        salary_min = request.POST.get('salary_min')
        salary_max = request.POST.get('salary_max')
        skills = request.POST.get('skills', '').split(',')
        skills = [s.strip() for s in skills if s.strip()]
        
        job = Job.objects.create(
            title=title,
            company=company,
            description=description,
            requirements=requirements,
            responsibilities=responsibilities,
            job_type=job_type,
            experience_level=experience_level,
            location=location,
            is_remote=is_remote,
            salary_min=salary_min or None,
            salary_max=salary_max or None,
            skills_required=skills,
            posted_by=request.user,
            is_approved=True,
            is_verified=False,
        )
        
        ai_result = job.ai_verify()
        
        messages.success(request, f'✅ Job posted successfully! AI Score: {ai_result["score"]}%')
        return redirect('my_jobs')
    
    return render(request, 'jobs/post_job.html', {
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def my_jobs(request):
    if request.user.user_type != 'recruiter':
        return redirect('job_list')
    
    jobs = Job.objects.filter(posted_by=request.user)
    return render(request, 'jobs/my_jobs.html', {
        'jobs': jobs,
    })


@login_required
def apply_job(request, job_id):
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can apply.')
        return redirect('job_detail', job_id=job_id)
    
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied to this job.')
        return redirect('job_detail', job_id=job_id)
    
    if request.method == 'POST':
        cover_letter = request.POST.get('cover_letter', '')
        
        application = JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=cover_letter,
            status='pending'
        )
        
        messages.success(request, 'Application submitted successfully!')
        return redirect('my_applications')
    
    return render(request, 'jobs/apply_job.html', {
        'job': job,
    })


@login_required
def my_applications(request):
    if request.user.user_type != 'candidate':
        return redirect('job_list')
    
    applications = JobApplication.objects.filter(
        applicant=request.user
    ).select_related('job')
    
    return render(request, 'jobs/my_applications.html', {
        'applications': applications,
    })


@login_required
def manage_applications(request, job_id):
    if request.user.user_type != 'recruiter':
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    applications = JobApplication.objects.filter(job=job)
    
    if request.method == 'POST':
        application_id = request.POST.get('application_id')
        new_status = request.POST.get('status')
        feedback = request.POST.get('feedback', '')
        
        application = get_object_or_404(JobApplication, id=application_id, job=job)
        
        if new_status:
            application.status = new_status
        
        if feedback:
            application.recruiter_feedback = feedback
            application.recruiter_feedback_date = timezone.now()
        
        application.save()
        messages.success(request, 'Application updated successfully!')
        
        return redirect('manage_applications', job_id=job_id)
    
    return render(request, 'jobs/manage_applications.html', {
        'job': job,
        'applications': applications,
        'status_choices': JobApplication.STATUS_CHOICES,
    })


@login_required
def edit_job(request, job_id):
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can edit jobs.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    
    if request.method == 'POST':
        job.title = request.POST.get('title')
        job.company = request.POST.get('company')
        job.description = request.POST.get('description')
        job.requirements = request.POST.get('requirements')
        job.responsibilities = request.POST.get('responsibilities', '')
        job.job_type = request.POST.get('job_type')
        job.experience_level = request.POST.get('experience_level')
        job.location = request.POST.get('location')
        job.is_remote = request.POST.get('is_remote') == 'on'
        job.salary_min = request.POST.get('salary_min') or None
        job.salary_max = request.POST.get('salary_max') or None
        skills = request.POST.get('skills', '').split(',')
        job.skills_required = [s.strip() for s in skills if s.strip()]
        job.save()
        
        ai_result = job.ai_verify()
        
        messages.success(request, f'✅ Job updated successfully! AI Score: {ai_result["score"]}%')
        return redirect('my_jobs')
    
    return render(request, 'jobs/edit_job.html', {
        'job': job,
        'job_types': Job.JOB_TYPES,
        'experience_levels': Job.EXPERIENCE_LEVELS,
    })


@login_required
def toggle_job_status(request, job_id):
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can change job status.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    job.is_active = not job.is_active
    job.save()
    
    status = 'activated' if job.is_active else 'deactivated'
    messages.success(request, f'Job {status} successfully!')
    return redirect('my_jobs')


@login_required
def delete_job(request, job_id):
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can delete jobs.')
        return redirect('job_list')
    
    job = get_object_or_404(Job, id=job_id, posted_by=request.user)
    
    if request.GET.get('confirm') == 'yes':
        job_title = job.title
        job.delete()
        messages.success(request, f'Job "{job_title}" deleted successfully!')
        return redirect('my_jobs')
    
    return render(request, 'jobs/delete_job.html', {
        'job': job,
    })


@login_required
def view_cv(request, application_id):
    """View CV of an applicant"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can view CVs.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id)
    
    if application.job.posted_by != request.user:
        messages.error(request, 'You are not authorized to view this CV.')
        return redirect('job_list')
    
    try:
        profile = CandidateProfile.objects.get(user=application.applicant)
        
        if not profile.cv_file:
            messages.error(request, 'Candidate has not uploaded a CV yet.')
            return redirect('manage_applications', job_id=application.job.id)
        
        return redirect(profile.cv_file.url)
        
    except CandidateProfile.DoesNotExist:
        messages.error(request, 'Candidate profile not found.')
        return redirect('manage_applications', job_id=application.job.id)
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('manage_applications', job_id=application.job.id)


@login_required
def download_cv(request, application_id):
    """Download CV of an applicant"""
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can download CVs.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id)
    
    if application.job.posted_by != request.user:
        messages.error(request, 'You are not authorized to download this CV.')
        return redirect('job_list')
    
    try:
        profile = CandidateProfile.objects.get(user=application.applicant)
        
        if not profile.cv_file:
            messages.error(request, 'Candidate has not uploaded a CV yet.')
            return redirect('manage_applications', job_id=application.job.id)
        
        return redirect(profile.cv_file.url)
        
    except CandidateProfile.DoesNotExist:
        messages.error(request, 'Candidate profile not found.')
        return redirect('manage_applications', job_id=application.job.id)
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('manage_applications', job_id=application.job.id)


@login_required
def withdraw_application(request, application_id):
    """Withdraw a job application"""
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can withdraw applications.')
        return redirect('job_list')
    
    application = get_object_or_404(JobApplication, id=application_id, applicant=request.user)
    
    if application.status == 'withdrawn':
        messages.warning(request, 'Application already withdrawn.')
        return redirect('my_applications')
    
    if application.status in ['hired', 'rejected']:
        messages.error(request, f'Cannot withdraw {application.status} application.')
        return redirect('my_applications')
    
    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()
        messages.success(request, f'Application for "{application.job.title}" withdrawn successfully!')
        return redirect('my_applications')
    
    return render(request, 'jobs/withdraw_confirm.html', {
        'application': application,
    })


@login_required
def search_candidates(request):
    if request.user.user_type != 'recruiter':
        messages.error(request, 'Only recruiters can search candidates.')
        return redirect('job_list')
    
    query = request.GET.get('query', '')
    skill_filter = request.GET.get('skill', '')
    fraud_filter = request.GET.get('fraud', '')
    
    candidates = User.objects.filter(user_type='candidate')
    results = []
    
    for candidate in candidates:
        try:
            profile = CandidateProfile.objects.get(user=candidate)
            cv_analysis = CVAnalysis.objects.filter(candidate=candidate).first()
            
            match = False
            
            if query:
                if query.lower() in candidate.username.lower() or query.lower() in candidate.email.lower():
                    match = True
            
            if skill_filter:
                if skill_filter.lower() in [s.lower() for s in profile.skills]:
                    match = True
            
            if fraud_filter and cv_analysis:
                if fraud_filter.lower() == cv_analysis.fraud_risk_level.lower():
                    match = True
            
            if not query and not skill_filter and not fraud_filter:
                match = True
            
            if match and cv_analysis:
                results.append({
                    'candidate': candidate,
                    'profile': profile,
                    'cv_analysis': cv_analysis,
                    'skills': profile.skills[:10],
                    'certifications': profile.certifications[:5],
                    'fraud_score': cv_analysis.fraud_score_percentage,
                    'risk_level': cv_analysis.fraud_risk_level,
                })
        except:
            continue
    
    all_skills = set()
    for candidate in User.objects.filter(user_type='candidate'):
        try:
            profile = CandidateProfile.objects.get(user=candidate)
            all_skills.update(profile.skills)
        except:
            continue
    
    return render(request, 'jobs/search_candidates.html', {
        'results': results,
        'query': query,
        'skill_filter': skill_filter,
        'fraud_filter': fraud_filter,
        'all_skills': sorted(all_skills),
        'total_results': len(results),
    })


@login_required
def job_stats_api(request):
    if request.user.user_type != 'recruiter':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    jobs = Job.objects.filter(posted_by=request.user)
    total_jobs = jobs.count()
    total_applications = JobApplication.objects.filter(job__in=jobs).count()
    
    return JsonResponse({
        'total_jobs': total_jobs,
        'total_applications': total_applications,
    })
