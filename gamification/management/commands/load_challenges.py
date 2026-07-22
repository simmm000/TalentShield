# gamification/management/commands/load_challenges.py

from django.core.management.base import BaseCommand
from gamification.models import Challenge

class Command(BaseCommand):
    help = 'Load sample cybersecurity challenges'

    def handle(self, *args, **options):
        challenges = [
            {
                'title': 'Identify the Phishing Email',
                'description': 'Analyze the email headers and content to determine if it\'s a phishing attempt.',
                'category': 'incident_response',
                'difficulty': 'beginner',
                'question': 'You received an email claiming to be from your bank asking you to verify your account. What are the red flags in this email?',
                'scenario': 'Email from "security@bank-secure.com" claims your account has been compromised and asks you to click a link to verify your identity. The link goes to "bank-verify.xyz".',
                'options': [],
                'correct_answer': 'suspicious sender domain, urgent language, request for sensitive information',
                'answer_type': 'text',
                'hints': ['Check the sender\'s domain', 'Look for urgent language'],
                'points': 10,
                'time_limit_seconds': 180,
                'is_active': True
            },
            {
                'title': 'Network Port Analysis',
                'description': 'Identify common ports for network services.',
                'category': 'network_security',
                'difficulty': 'beginner',
                'question': 'Which port is commonly used for HTTPS traffic?',
                'scenario': 'You are performing a network scan and see traffic on multiple ports.',
                'options': ['80', '443', '22', '21'],
                'correct_answer': '443',
                'answer_type': 'multiple_choice',
                'hints': ['Think about secure web traffic', 'Not port 80'],
                'points': 10,
                'time_limit_seconds': 60,
                'is_active': True
            },
            {
                'title': 'SQL Injection Detection',
                'description': 'Identify SQL injection vulnerabilities in code.',
                'category': 'web_security',
                'difficulty': 'intermediate',
                'question': 'Which of these code snippets is vulnerable to SQL injection?',
                'scenario': 'You are reviewing code for a web application.',
                'options': [
                    'cursor.execute("SELECT * FROM users WHERE id = %s", user_id)',
                    'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
                    'cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))'
                ],
                'correct_answer': 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
                'answer_type': 'multiple_choice',
                'hints': ['Look for string interpolation', 'Parameterized queries are safe'],
                'points': 20,
                'time_limit_seconds': 120,
                'is_active': True
            },
            {
                'title': 'Incident Response Triage',
                'description': 'Prioritize incidents based on severity.',
                'category': 'incident_response',
                'difficulty': 'intermediate',
                'question': 'What should be the FIRST action when a ransomware alert is triggered?',
                'scenario': 'You are the SOC analyst on duty and receive an alert about potential ransomware activity.',
                'options': [],
                'correct_answer': 'isolate affected system from network to prevent spread',
                'answer_type': 'text',
                'hints': ['Consider containment first', 'Don\'t jump to recovery'],
                'points': 15,
                'time_limit_seconds': 90,
                'is_active': True
            },
            {
                'title': 'RSA Cryptography Basics',
                'description': 'Understand RSA encryption fundamentals.',
                'category': 'cryptography',
                'difficulty': 'advanced',
                'question': 'In RSA encryption, what is the relationship between the public key, private key, and modulus?',
                'scenario': 'You are explaining RSA to a junior security analyst.',
                'options': [],
                'correct_answer': 'public key is (e, n) and private key is (d, n) where n is the product of two primes',
                'answer_type': 'text',
                'hints': ['Think about key generation', 'n is the modulus'],
                'points': 25,
                'time_limit_seconds': 300,
                'is_active': True
            }
        ]

        for data in challenges:
            Challenge.objects.get_or_create(
                title=data['title'],
                defaults=data
            )
            self.stdout.write(f"✅ Added challenge: {data['title']}")

        self.stdout.write(self.style.SUCCESS('✅ All challenges loaded successfully!'))
        