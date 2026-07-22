# gamification/views.py - COMPLETE WITH SKILL RECOGNITION (LEVEL-BASED BADGES)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
import json
from .models import Challenge, ChallengeAttempt, Achievement, UserAchievement, GamificationProfile


@login_required
def challenges_list(request):
    """Display all available challenges"""
    if request.user.user_type != 'candidate':
        messages.info(request, 'Challenges are for candidates only. Check out jobs instead!')
        return redirect('job_list')
    
    attempted_ids = ChallengeAttempt.objects.filter(
        candidate=request.user,
        is_correct=True
    ).values_list('challenge_id', flat=True)
    
    challenges = Challenge.objects.filter(is_active=True).exclude(id__in=attempted_ids)
    
    profile, _ = GamificationProfile.objects.get_or_create(candidate=request.user)
    profile.update_cv_boost()
    profile.save()
    
    return render(request, 'gamification/challenges.html', {
        'challenges': challenges,
        'profile': profile,
    })


@login_required
def challenge_detail(request, challenge_id):
    """Show a specific challenge"""
    if request.user.user_type != 'candidate':
        messages.info(request, 'Challenges are for candidates only.')
        return redirect('job_list')
    
    challenge = get_object_or_404(Challenge, id=challenge_id, is_active=True)
    
    already_passed = ChallengeAttempt.objects.filter(
        candidate=request.user,
        challenge=challenge,
        is_correct=True
    ).exists()
    
    if already_passed:
        return JsonResponse({'error': 'Challenge already completed'}, status=400)
    
    return render(request, 'gamification/challenge_detail.html', {
        'challenge': challenge
    })


@csrf_exempt
@login_required
def submit_challenge(request, challenge_id):
    """Submit answer for a challenge"""
    if request.user.user_type != 'candidate':
        return JsonResponse({'error': 'Only candidates can submit challenges'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    challenge = get_object_or_404(Challenge, id=challenge_id, is_active=True)
    
    already_passed = ChallengeAttempt.objects.filter(
        candidate=request.user,
        challenge=challenge,
        is_correct=True
    ).exists()
    
    if already_passed:
        return JsonResponse({'error': 'Challenge already completed'}, status=400)
    
    try:
        data = json.loads(request.body)
        submitted_answer = data.get('answer', '')
        time_taken = data.get('time_taken', 0)
    except:
        return JsonResponse({'error': 'Invalid data'}, status=400)
    
    is_correct = evaluate_answer(challenge, submitted_answer)
    score = calculate_score(is_correct, time_taken, challenge.time_limit_seconds)
    
    attempt = ChallengeAttempt.objects.create(
        candidate=request.user,
        challenge=challenge,
        submitted_answer=submitted_answer,
        is_correct=is_correct,
        score=score,
        time_taken_seconds=time_taken,
        status='passed' if is_correct else 'failed',
        completed_at=timezone.now()
    )
    
    if is_correct:
        profile, _ = GamificationProfile.objects.get_or_create(candidate=request.user)
        
        points_earned = challenge.points
        if time_taken < challenge.time_limit_seconds * 0.5:
            points_earned += 5
        
        profile.add_points(max(points_earned, 1))
        
        profile.challenges_attempted += 1
        profile.challenges_passed += 1
        
        all_passed = ChallengeAttempt.objects.filter(
            candidate=request.user,
            is_correct=True
        )
        if all_passed.exists():
            total_score = sum([a.score for a in all_passed])
            profile.average_score = round(total_score / all_passed.count(), 1)
        
        today = timezone.now().date()
        if profile.last_activity:
            last_date = profile.last_activity.date()
            days_diff = (today - last_date).days
            if days_diff == 1:
                profile.current_streak_days += 1
            elif days_diff > 1:
                profile.current_streak_days = 0
        else:
            profile.current_streak_days = 1
        
        if profile.current_streak_days > profile.longest_streak_days:
            profile.longest_streak_days = profile.current_streak_days
        
        profile.last_activity = timezone.now()
        profile.update_cv_boost()
        profile.save()
        
        check_achievements(request.user)
    
    return JsonResponse({
        'success': True,
        'is_correct': is_correct,
        'score': score,
        'points_earned': challenge.points if is_correct else 0,
        'message': 'Correct! 🎉' if is_correct else 'Incorrect. Try again!'
    })


def evaluate_answer(challenge, submitted_answer):
    """Evaluate if answer is correct"""
    if challenge.answer_type == 'multiple_choice':
        return str(submitted_answer).strip().lower() == str(challenge.correct_answer).strip().lower()
    else:
        clean_answer = str(submitted_answer).lower().strip()
        clean_correct = str(challenge.correct_answer).lower().strip()
        
        key_phrases = [p.strip() for p in clean_correct.split(',')]
        matches = sum(1 for phrase in key_phrases if phrase in clean_answer)
        match_ratio = matches / len(key_phrases) if key_phrases else 0
        
        return match_ratio >= 0.4


def calculate_score(is_correct, time_taken, time_limit):
    """Calculate score based on correctness and time"""
    if not is_correct:
        return 0.0
    
    time_ratio = min(time_taken / time_limit, 1.0)
    time_score = (1 - time_ratio) * 30
    base_score = 70
    total_score = min(base_score + time_score, 100)
    return round(total_score, 1)


def check_achievements(user):
    """Check and award achievements"""
    profile, _ = GamificationProfile.objects.get_or_create(candidate=user)
    
    if profile.challenges_passed >= 10:
        award_achievement(user, 'challenge_master', '🏆 Challenge Master', 'Completed 10 cybersecurity challenges')
    
    if profile.average_score > 80:
        award_achievement(user, 'top_performer', '⭐ Top Performer', 'Average challenge score above 80%')
    
    today = timezone.now().date()
    today_passed = ChallengeAttempt.objects.filter(
        candidate=user,
        is_correct=True,
        completed_at__date=today
    ).count()
    
    if today_passed >= 5:
        award_achievement(user, 'quick_learner', '🚀 Quick Learner', 'Completed 5 challenges in one day')
    
    if profile.current_streak_days >= 7:
        award_achievement(user, 'streak_master', '🔥 Streak Master', '7+ day streak')


def award_achievement(user, achievement_type, name, description):
    """Award an achievement to user"""
    achievement, _ = Achievement.objects.get_or_create(
        type=achievement_type,
        defaults={
            'name': name,
            'description': description,
            'icon': '🏆',
            'points_bonus': 20
        }
    )
    
    user_achievement, created = UserAchievement.objects.get_or_create(
        candidate=user,
        achievement=achievement
    )
    
    if created:
        profile, _ = GamificationProfile.objects.get_or_create(candidate=user)
        if achievement.points_bonus > 0:
            profile.add_points(achievement.points_bonus)
            if achievement.name not in profile.badges:
                profile.badges.append(achievement.name)
                profile.badges_count += 1
                profile.save()


@login_required
def leaderboard(request):
    """Display leaderboard"""
    profiles = GamificationProfile.objects.filter(
        candidate__user_type='candidate'
    ).select_related('candidate').order_by('-total_points')[:20]
    
    return render(request, 'gamification/leaderboard.html', {
        'profiles': profiles
    })


@login_required
def my_profile(request):
    """Display user's gamification profile"""
    if request.user.user_type != 'candidate':
        messages.info(request, 'Gamification profile is for candidates only.')
        return redirect('dashboard')
    
    profile, _ = GamificationProfile.objects.get_or_create(candidate=request.user)
    profile.update_cv_boost()
    profile.save()
    
    recent_achievements = UserAchievement.objects.filter(
        candidate=request.user
    ).select_related('achievement').order_by('-earned_at')[:5]
    
    recent_attempts = ChallengeAttempt.objects.filter(
        candidate=request.user
    ).select_related('challenge').order_by('-completed_at')[:10]
    
    return render(request, 'gamification/profile.html', {
        'profile': profile,
        'recent_achievements': recent_achievements,
        'recent_attempts': recent_attempts
    })


# ============================================================
# ===== SKILL RECOGNITION (LEVEL-BASED BADGES) =====
# ============================================================

@login_required
def skill_recognition(request):
    """Show recognized skills and badges for candidate"""
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates can view skill recognition.')
        return redirect('dashboard')
    
    from accounts.models import CandidateProfile
    from .models import GamificationProfile
    
    try:
        candidate_profile = CandidateProfile.objects.get(user=request.user)
    except CandidateProfile.DoesNotExist:
        messages.error(request, 'Please complete your profile first.')
        return redirect('dashboard')
    
    profile, _ = GamificationProfile.objects.get_or_create(candidate=request.user)
    skills = candidate_profile.skills
    challenges_passed = profile.challenges_passed
    
    # Skill data
    skill_data = {
        'python': {'name': 'Python', 'badge': '🐍', 'color': '#3776AB', 'category': 'Programming'},
        'linux': {'name': 'Linux', 'badge': '🐧', 'color': '#FCC624', 'category': 'Operating Systems'},
        'windows': {'name': 'Windows', 'badge': '🪟', 'color': '#00A4EF', 'category': 'Operating Systems'},
        'network': {'name': 'Networking', 'badge': '🌐', 'color': '#0066CC', 'category': 'Networking'},
        'security': {'name': 'Security', 'badge': '🔒', 'color': '#22C55E', 'category': 'Security'},
        'wireshark': {'name': 'Wireshark', 'badge': '📡', 'color': '#1679A1', 'category': 'Security Tools'},
        'nmap': {'name': 'Nmap', 'badge': '🔍', 'color': '#2C3E50', 'category': 'Security Tools'},
        'metasploit': {'name': 'Metasploit', 'badge': '💥', 'color': '#C41230', 'category': 'Security Tools'},
        'firewall': {'name': 'Firewall', 'badge': '🧱', 'color': '#EA580C', 'category': 'Network Security'},
        'siem': {'name': 'SIEM', 'badge': '📊', 'color': '#7C3AED', 'category': 'Security Operations'},
        'splunk': {'name': 'Splunk', 'badge': '📊', 'color': '#00A4EF', 'category': 'Security Operations'},
        'ceh': {'name': 'CEH', 'badge': '🎯', 'color': '#DC2626', 'category': 'Certifications'},
        'comptia security+': {'name': 'Security+', 'badge': '🛡️', 'color': '#0EA5E9', 'category': 'Certifications'},
        'comptia security': {'name': 'Security+', 'badge': '🛡️', 'color': '#0EA5E9', 'category': 'Certifications'},
        'security+': {'name': 'Security+', 'badge': '🛡️', 'color': '#0EA5E9', 'category': 'Certifications'},
        'cissp': {'name': 'CISSP', 'badge': '🏆', 'color': '#1A1A2E', 'category': 'Certifications'},
        'oscp': {'name': 'OSCP', 'badge': '🔓', 'color': '#DC2626', 'category': 'Certifications'},
        'cisa': {'name': 'CISA', 'badge': '📋', 'color': '#2563EB', 'category': 'Certifications'},
        'cism': {'name': 'CISM', 'badge': '📋', 'color': '#7C3AED', 'category': 'Certifications'},
        'cryptography': {'name': 'Cryptography', 'badge': '🔐', 'color': '#8B5CF6', 'category': 'Security'},
        'penetration testing': {'name': 'Pen Testing', 'badge': '🎯', 'color': '#DC2626', 'category': 'Security'},
        'incident response': {'name': 'Incident Response', 'badge': '🚨', 'color': '#EF4444', 'category': 'Security Operations'},
        'vulnerability assessment': {'name': 'Vuln Assessment', 'badge': '🔎', 'color': '#F59E0B', 'category': 'Security'},
        'cloud': {'name': 'Cloud Security', 'badge': '☁️', 'color': '#3B82F6', 'category': 'Cloud'},
        'aws': {'name': 'AWS', 'badge': '☁️', 'color': '#FF9900', 'category': 'Cloud'},
        'azure': {'name': 'Azure', 'badge': '☁️', 'color': '#0078D4', 'category': 'Cloud'},
        'docker': {'name': 'Docker', 'badge': '🐳', 'color': '#2496ED', 'category': 'DevOps'},
        'kubernetes': {'name': 'Kubernetes', 'badge': '☸️', 'color': '#326CE5', 'category': 'DevOps'},
    }
    
    # ===== LEVEL-BASED BADGES =====
    if challenges_passed >= 20:
        level = 'Expert'
        level_color = '#8B5CF6'
        level_icon = '🏆'
        level_badge = '👑 Expert'
        next_level_challenges = 25
    elif challenges_passed >= 10:
        level = 'Advanced'
        level_color = '#F59E0B'
        level_icon = '⭐'
        level_badge = '🚀 Advanced'
        next_level_challenges = 20
    elif challenges_passed >= 5:
        level = 'Intermediate'
        level_color = '#3B82F6'
        level_icon = '🌟'
        level_badge = '💪 Intermediate'
        next_level_challenges = 10
    elif challenges_passed >= 3:
        level = 'Beginner'
        level_color = '#10B981'
        level_icon = '🌱'
        level_badge = '🌱 Beginner'
        next_level_challenges = 5
    else:
        level = 'Novice'
        level_color = '#6B7280'
        level_icon = '📚'
        level_badge = '📚 Novice'
        next_level_challenges = 3
    
    recognized_skills = []
    
    for skill in skills:
        skill_lower = skill.lower()
        if skill_lower in skill_data:
            data = skill_data[skill_lower]
            
            recognized_skills.append({
                'name': data['name'],
                'badge': data['badge'],
                'color': data['color'],
                'category': data['category'],
                'skill': skill,
                'level': level,
                'level_color': level_color,
                'level_icon': level_icon,
                'level_badge': level_badge,
                'challenges_passed': challenges_passed,
            })
    
    # Remove duplicates
    seen = set()
    unique_skills = []
    for item in recognized_skills:
        key = item['skill']
        if key not in seen:
            seen.add(key)
            unique_skills.append(item)
    
    # Count skills by category
    categories = {}
    for skill in unique_skills:
        cat = skill['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill)
    
    return render(request, 'gamification/skill_recognition.html', {
        'recognized_skills': unique_skills,
        'categories': categories,
        'level': level,
        'level_color': level_color,
        'level_icon': level_icon,
        'level_badge': level_badge,
        'next_level_challenges': next_level_challenges,
        'challenges_passed': challenges_passed,
        'total_points': profile.total_points,
        'total_skills': len(unique_skills),
        'skill_data': skill_data,
    })
