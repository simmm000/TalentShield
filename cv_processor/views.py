# cv_processor/views.py - CV SCORE ONLY

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from accounts.models import CandidateProfile
from .models import CVAnalysis
import re
import hashlib
import io
from datetime import datetime


class CVUploadAndAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        print("=" * 60)
        print("📤 CV Upload Request")
        print(f"User: {request.user.username}")
        print("=" * 60)
        
        try:
            if request.user.user_type != 'candidate':
                return Response(
                    {'error': 'Only candidates can upload CVs'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if 'cv_file' not in request.FILES:
                return Response(
                    {'error': 'No CV file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['cv_file']
            print(f"File: {file.name}, Size: {file.size}")
            
            if file.size > 5242880:
                return Response(
                    {'error': 'File too large (max 5MB)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            text = self.extract_text(file)
            print(f"Text length: {len(text)}")
            
            if len(text) < 50:
                file_content = file.read()
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_path = tmp_file.name
                
                try:
                    with open(tmp_path, 'rb') as f:
                        import PyPDF2
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() or ""
                    os.unlink(tmp_path)
                except:
                    os.unlink(tmp_path)
                    text = ""
                
                file.seek(0)
                print(f"After alternative extraction: {len(text)}")
            
            parsed_data = self.parse_cv(text)
            print(f"Skills: {len(parsed_data['skills'])} skills detected")
            print(f"Certifications: {len(parsed_data['certifications'])} certs detected")
            print(f"Experience: {parsed_data['experience_years']} years")
            
            # ===== CV QUALITY SCORE =====
            cv_score_result = self.calculate_cv_score(parsed_data)
            print(f"CV Score: {cv_score_result['score']}% - {cv_score_result['quality']}")
            
            # ===== FRAUD DETECTION =====
            fraud_result = self.calculate_fraud_score(parsed_data, request.user)
            print(f"Fraud Score: {fraud_result['fraud_score_percentage']}")
            print(f"Risk Level: {fraud_result['risk_level']}")
            
            profile, created = CandidateProfile.objects.get_or_create(user=request.user)
            
            profile.skills = parsed_data['skills']
            profile.certifications = parsed_data['certifications']
            profile.experience_years = parsed_data['experience_years']
            profile.cv_text = text
            
            file.seek(0)
            filename = f"cv_{request.user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            saved_path = default_storage.save(f'cvs/{filename}', ContentFile(file.read()))
            profile.cv_file = saved_path
            profile.save()
            
            cv_analysis = CVAnalysis.objects.create(
                candidate=request.user,
                extracted_skills=parsed_data['skills'],
                extracted_certifications=parsed_data['certifications'],
                experience_years=parsed_data['experience_years'],
                fraud_score=fraud_result['fraud_score'],
                fraud_risk_level=fraud_result['risk_level'],
                fraud_details=fraud_result,
                cv_hash=fraud_result['cv_hash'],
                cv_content_hash=fraud_result['cv_content_hash'],
            )
            
            print("✅ Success!")
            
            return Response({
                'success': True,
                'message': 'CV analyzed successfully',
                'parsed_data': {
                    'skills': parsed_data['skills'],
                    'certifications': parsed_data['certifications'],
                    'experience_years': parsed_data['experience_years'],
                },
                'cv_score': {
                    'score': cv_score_result['score'],
                    'quality': cv_score_result['quality'],
                    'emoji': cv_score_result['emoji'],
                    'description': cv_score_result['description'],
                    'reasons': cv_score_result['reasons'],
                    'suggestions': cv_score_result['suggestions'],
                    'details': {
                        'skills': cv_score_result['skill_count'],
                        'certifications': cv_score_result['cert_count'],
                        'experience': cv_score_result['experience_years'],
                        'word_count': cv_score_result['word_count'],
                    }
                },
                'fraud_analysis': {
                    'fraud_score': fraud_result['fraud_score_percentage'],
                    'risk_level': fraud_result['risk_level'],
                    'duplicate_detected': fraud_result.get('duplicate_found', False),
                    'fraud_factors': fraud_result.get('fraud_factors', []),
                },
                'analysis_id': cv_analysis.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def extract_text(self, file):
        text = ""
        try:
            if file.name.lower().endswith('.pdf'):
                import PyPDF2
                file_content = file.read()
                pdf_file = io.BytesIO(file_content)
                reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(reader.pages)):
                    try:
                        page = reader.pages[page_num]
                        text += page.extract_text() or ""
                    except:
                        continue
                file.seek(0)
            elif file.name.lower().endswith('.docx'):
                import docx
                doc = docx.Document(file)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                text = file.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"⚠️ Text extraction error: {e}")
            try:
                file.seek(0)
                content = file.read()
                text = content.decode('utf-8', errors='ignore')
                text = re.sub(r'[^\x00-\x7F]+', ' ', text)
                text = re.sub(r'\s+', ' ', text)
            except:
                text = ""
            file.seek(0)
        return text
    
    def parse_cv(self, text):
        text_lower = text.lower()
        
        skills_list = [
            'python', 'java', 'c++', 'javascript', 'linux', 'windows',
            'network', 'firewall', 'wireshark', 'nmap', 'metasploit',
            'penetration testing', 'vulnerability assessment', 'incident response',
            'siem', 'splunk', 'owasp', 'sql', 'docker', 'kubernetes',
            'cloud', 'aws', 'azure', 'security', 'compliance', 'html', 'css',
            'php', 'ruby', 'bash', 'powershell', 'active directory',
            'tcp/ip', 'dns', 'dhcp', 'vpn', 'routing', 'switching',
            'burp suite', 'nessus', 'openvas', 'snort', 'suricata',
            'kali linux', 'threat analysis', 'risk assessment',
            'security auditing', 'forensics', 'malware analysis',
            'phishing detection', 'zero trust', 'security architecture',
            'iam', 'security groups', 'cloudtrail', 'scapy', 'ansible'
        ]
        
        skills = []
        for skill in skills_list:
            if skill in text_lower:
                skills.append(skill)
        
        skills_section = re.search(r'skills[:]\s*(.*?)(?=\n\n|\n[a-z]|$)', text_lower, re.DOTALL)
        if skills_section:
            skill_text = skills_section.group(1)
            skill_items = re.split(r'[, \n•-]+', skill_text)
            for item in skill_items:
                item = item.strip()
                if item and len(item) > 2 and item not in skills and item not in ['skills']:
                    skills.append(item)
        
        skills = list(set(skills))
        
        cert_patterns = {
            'CEH': r'ceh',
            'CompTIA Security+': r'security\+|comptia security',
            'CISSP': r'cissp',
            'OSCP': r'oscp',
            'CISA': r'cisa',
            'CISM': r'cism',
            'AWS Certified Security': r'aws certified security',
            'ISO 27001 Lead Auditor': r'iso 27001',
            'CCNA': r'ccna',
            'CCNP': r'ccnp',
        }
        
        certifications = []
        for name, pattern in cert_patterns.items():
            if re.search(pattern, text_lower):
                certifications.append({'name': name})
        
        experience_years = 0.0
        
        year_patterns = re.findall(r'(\d+)\+?\s*(?:years|yrs)', text_lower)
        if year_patterns:
            experience_years = float(year_patterns[0])
        
        date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present)'
        matches = re.findall(date_pattern, text_lower, re.IGNORECASE)
        for start, end in matches:
            try:
                start_year = int(start)
                end_year = datetime.now().year if end.lower() == 'present' else int(end)
                experience_years += (end_year - start_year)
            except:
                continue
        
        if experience_years == 0:
            exp_match = re.search(r'(\d+)\s*\+\s*years', text_lower)
            if exp_match:
                experience_years = float(exp_match.group(1))
        
        return {
            'cv_text': text,
            'skills': skills,
            'certifications': certifications,
            'experience_years': round(experience_years, 1)
        }
    
    # ===== CV QUALITY SCORE (0-100) =====
    def calculate_cv_score(self, parsed_data):
        """Calculate CV Quality Score (0-100)"""
        score = 0
        reasons = []
        suggestions = []
        
        text = parsed_data['cv_text']
        skill_count = len(parsed_data['skills'])
        cert_count = len(parsed_data['certifications'])
        exp_years = parsed_data['experience_years']
        word_count = len(text.split())
        
        # 1. Skills (30 points)
        if skill_count >= 10:
            score += 30
            reasons.append('✅ Excellent: 10+ skills found')
        elif skill_count >= 5:
            score += 20
            reasons.append('✅ Good: 5+ skills found')
        elif skill_count >= 3:
            score += 10
            reasons.append('⚠️ Average: Only 3 skills found')
        else:
            reasons.append('❌ Poor: Less than 3 skills found')
            suggestions.append('Add more cybersecurity skills (Python, Linux, Network Security)')
        
        # 2. Certifications (20 points)
        if cert_count >= 3:
            score += 20
            reasons.append('✅ Excellent: 3+ certifications')
        elif cert_count >= 1:
            score += 10
            reasons.append('✅ Good: Has certifications')
        else:
            reasons.append('❌ No certifications found')
            suggestions.append('Get certifications like CEH, CompTIA Security+, or CISSP')
        
        # 3. Experience (20 points)
        if exp_years >= 5:
            score += 20
            reasons.append('✅ Excellent: 5+ years experience')
        elif exp_years >= 2:
            score += 15
            reasons.append('✅ Good: 2+ years experience')
        elif exp_years >= 1:
            score += 10
            reasons.append('⚠️ Average: 1 year experience')
        else:
            reasons.append('❌ No experience found')
            suggestions.append('Add internships or project experience')
        
        # 4. CV Length (10 points)
        if word_count >= 500:
            score += 10
            reasons.append('✅ Good CV length')
        elif word_count >= 200:
            score += 5
            reasons.append('⚠️ Average CV length')
        else:
            reasons.append('❌ CV too short')
            suggestions.append('Add more details to your CV')
        
        # 5. Format/Structure (10 points)
        structure_points = 0
        text_lower = text.lower()
        if 'education' in text_lower or 'degree' in text_lower:
            structure_points += 3
        if 'experience' in text_lower or 'work' in text_lower:
            structure_points += 3
        if 'skill' in text_lower or 'certification' in text_lower:
            structure_points += 4
        score += structure_points
        reasons.append(f'✅ Structure: {structure_points}/10 points')
        
        # 6. Projects (10 points)
        if 'project' in text_lower:
            score += 10
            reasons.append('✅ Projects included')
        else:
            reasons.append('⚠️ No projects mentioned')
            suggestions.append('Add project experience to strengthen CV')
        
        score = min(score, 100)
        
        if score >= 80:
            quality = 'Excellent'
            emoji = '🌟'
            description = 'Your CV is highly professional and complete. Great job!'
        elif score >= 60:
            quality = 'Good'
            emoji = '📄'
            description = 'Your CV is decent but can be improved.'
        elif score >= 40:
            quality = 'Average'
            emoji = '📃'
            description = 'Your CV needs more content and structure.'
        else:
            quality = 'Poor'
            emoji = '📄'
            description = 'Your CV is incomplete. Please add more details.'
        
        return {
            'score': score,
            'quality': quality,
            'emoji': emoji,
            'description': description,
            'reasons': reasons,
            'suggestions': suggestions,
            'skill_count': skill_count,
            'cert_count': cert_count,
            'experience_years': exp_years,
            'word_count': word_count,
        }
    
    # ===== FRAUD DETECTION =====
    def calculate_fraud_score(self, parsed_data, user):
        """Calculate fraud score"""
        fraud_score = 0.0
        fraud_factors = []
        duplicate_found = False
        
        # 1. AI-generated text detection (25%)
        ai_patterns = [
            'as a large language model', 'I am an AI', 'generated by',
            'chatgpt', 'openai', 'proficient in a wide range'
        ]
        for pattern in ai_patterns:
            if pattern in parsed_data['cv_text'].lower():
                fraud_score += 0.25
                fraud_factors.append({
                    'factor': '🤖 AI-Generated Text Detected',
                    'impact': '+25%'
                })
                break
        
        # 2. Too many certifications (20%)
        cert_count = len(parsed_data['certifications'])
        if cert_count > 8:
            fraud_score += 0.20
            fraud_factors.append({
                'factor': f'📜 Too many certifications ({cert_count})',
                'impact': '+20%'
            })
        
        # 3. Experience inflation (20%)
        try:
            profile = CandidateProfile.objects.get(user=user)
            if profile.graduation_year:
                current_year = datetime.now().year
                max_exp = current_year - profile.graduation_year
                if parsed_data['experience_years'] > max_exp + 2:
                    fraud_score += 0.20
                    fraud_factors.append({
                        'factor': '⏰ Experience Inflation',
                        'impact': '+20%'
                    })
        except:
            pass
        
        # 4. Duplicate CV (20%)
        clean_text = ' '.join(parsed_data['cv_text'].lower().split())[:500]
        cv_hash = hashlib.sha256(clean_text.encode()).hexdigest()
        existing = CVAnalysis.objects.filter(cv_content_hash=cv_hash).exclude(candidate=user)
        if existing.exists():
            fraud_score += 0.20
            duplicate_found = True
            fraud_factors.append({
                'factor': '🔄 Duplicate CV Detected',
                'impact': '+20%'
            })
        
        # 5. No skills (10%)
        if len(parsed_data['skills']) == 0:
            fraud_score += 0.10
            fraud_factors.append({
                'factor': '📭 No Skills Detected',
                'impact': '+10%'
            })
        
        fraud_score = min(fraud_score, 1.0)
        
        if fraud_score >= 0.7:
            risk_level = 'High'
        elif fraud_score >= 0.4:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        return {
            'fraud_score': round(fraud_score, 3),
            'fraud_score_percentage': f"{round(fraud_score * 100, 1)}%",
            'risk_level': risk_level,
            'fraud_factors': fraud_factors,
            'duplicate_found': duplicate_found,
            'cv_hash': cv_hash,
            'cv_content_hash': cv_hash,
        }
    