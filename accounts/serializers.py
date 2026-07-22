# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CandidateProfile, RecruiterProfile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'user_type', 'phone']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'candidate')
        )
        return user


class CandidateProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    gamification_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateProfile
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def get_gamification_profile(self, obj):
        from gamification.models import GamificationProfile
        try:
            profile = GamificationProfile.objects.get(candidate=obj.user)
            return {
                'total_points': profile.total_points,
                'level': profile.level,
                'challenges_passed': profile.challenges_passed,
                'cv_boost_percentage': profile.cv_boost_percentage,
                'badges_count': profile.badges_count,
            }
        except:
            return None
        