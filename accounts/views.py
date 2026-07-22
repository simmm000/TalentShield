# accounts/views.py - COMPLETE FIXED

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, CandidateProfile, RecruiterProfile

# ===== REST FRAMEWORK IMPORTS =====
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import CandidateProfileSerializer

# ===== FORGOT PASSWORD IMPORTS =====
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
import urllib.parse
import re

User = get_user_model()


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        user_type = request.POST.get('user_type', 'candidate')
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'accounts/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'accounts/register.html')
        
        try:
            validate_password(password, user=None)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'accounts/register.html')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )
        
        if user_type == 'candidate':
            CandidateProfile.objects.create(user=user)
        elif user_type == 'recruiter':
            RecruiterProfile.objects.create(user=user, company='')
        
        login(request, user)
        messages.success(request, 'Registration successful!')
        return redirect('dashboard')
    
    return render(request, 'accounts/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    if request.user.user_type != 'candidate':
        messages.error(request, 'Only candidates have profiles.')
        return redirect('dashboard')
    
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile.date_of_birth = request.POST.get('date_of_birth') or None
        graduation_year = request.POST.get('graduation_year')
        if graduation_year:
            profile.graduation_year = int(graduation_year)
        profile.institution = request.POST.get('institution', '')
        profile.degree = request.POST.get('degree', '')
        
        manual_skills = request.POST.get('manual_skills', '')
        if manual_skills:
            skills_list = [s.strip() for s in manual_skills.split(',') if s.strip()]
            existing_skills = set(profile.skills)
            existing_skills.update(skills_list)
            profile.skills = list(existing_skills)
        
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    from cv_processor.models import CVAnalysis
    cv_analysis = CVAnalysis.objects.filter(candidate=request.user).first()
    
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'cv_analysis': cv_analysis,
    })


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = CandidateProfile.objects.get(user=request.user)
            serializer = CandidateProfileSerializer(profile)
            return Response(serializer.data)
        except CandidateProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)


# ============================================================
# ===== FORGOT PASSWORD - FIXED =====
# ============================================================

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Fix: Proper URL encoding for token
            import urllib.parse
            encoded_token = urllib.parse.quote(token, safe='')
            
            reset_link = f"http://talentshield.local:8000/reset-password/{uid}/{encoded_token}/"
            
            subject = 'Password Reset Request - Talent Shield'
            message = f"""
            Hello {user.username},

            You requested a password reset. Click the link below to reset your password:

            {reset_link}

            If you didn't request this, please ignore this email.

            Thanks,
            Talent Shield Team
            """
            
            send_mail(subject, message, 'noreply@talentshield.com', [email])
            messages.success(request, 'Password reset link sent to your email!')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'No user found with this email address.')
            return render(request, 'accounts/forgot_password.html')
    
    return render(request, 'accounts/forgot_password.html')


def reset_password_view(request, uidb64, token):
    import urllib.parse
    
    # Fix: Properly decode the token
    try:
        token = urllib.parse.unquote(token)
    except:
        token = token.replace('%3D', '=')
    
    print(f"🔍 Token: {token}")
    print(f"🔍 UID: {uidb64}")
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        print(f"✅ Token valid for user: {user.username}")
        if request.method == 'POST':
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            
            if password != password2:
                messages.error(request, 'Passwords do not match')
                return render(request, 'accounts/reset_password.html', {'valid': True})
            
            try:
                validate_password(password, user=user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'accounts/reset_password.html', {'valid': True})
            
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successfully! Please login.')
            return redirect('login')
        
        return render(request, 'accounts/reset_password.html', {'valid': True})
    else:
        print(f"❌ Invalid token for user: {user}")
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('forgot_password')
    