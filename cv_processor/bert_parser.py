# cv_processor/bert_parser.py
"""
BERT-based CV parsing: Named Entity Recognition + semantic embeddings.
"""

import re
import threading
from datetime import datetime

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from sentence_transformers import SentenceTransformer


class BERTCVProcessor:
    def __init__(self):
        # Semantic embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # BERT NER pipeline
        tokenizer = AutoTokenizer.from_pretrained('dslim/bert-base-NER')
        model = AutoModelForTokenClassification.from_pretrained('dslim/bert-base-NER')
        device = 0 if torch.cuda.is_available() else -1
        self.ner_pipeline = pipeline(
            'ner',
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy='simple',
            device=device,
        )

        # Skill lists
        self.cyber_skills = {
            'technical': ['python', 'java', 'c++', 'javascript', 'bash', 'powershell', 'sql', 'linux',
                          'windows', 'network', 'tcp/ip', 'firewall', 'ids', 'ips', 'vpn', 'wireshark',
                          'nmap', 'metasploit', 'burp suite', 'owasp', 'siem', 'splunk', 'elasticsearch'],
            'security': ['penetration testing', 'vulnerability assessment', 'threat analysis', 'incident response',
                         'risk assessment', 'security audit', 'compliance', 'gdpr', 'hipaa', 'iso 27001'],
            'tools': ['wireshark', 'nmap', 'metasploit', 'burpsuite', 'sqlmap', 'nessus', 'openvas',
                      'snort', 'suricata', 'zeek', 'splunk', 'qradar', 'arcsight'],
        }
        self.all_skills = set(
            self.cyber_skills['technical'] + self.cyber_skills['security'] + self.cyber_skills['tools']
        )

    def extract_text_from_cv(self, file):
        text = ""
        name = file.name.lower()
        if name.endswith('.pdf'):
            import PyPDF2
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif name.endswith('.docx'):
            import docx
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            try:
                text = file.read().decode('utf-8', errors='ignore')
            except:
                text = ""
        return text

    def extract_entities(self, text):
        if not text:
            return []
        truncated = text[:2000]
        raw_entities = self.ner_pipeline(truncated)
        entities = []
        for ent in raw_entities:
            entities.append({
                'text': ent['word'],
                'type': ent['entity_group'],
                'confidence': round(float(ent['score']), 3),
            })
        return entities

    def extract_skills(self, text):
        text_lower = text.lower()
        return [skill for skill in self.all_skills if skill in text_lower]

    def extract_certifications(self, text):
        cert_patterns = {
            'CEH': r'CEH[:\s]*([A-Z0-9-]+)?',
            'CompTIA Security+': r'Security\+[:\s]*([A-Z0-9-]+)?',
            'CISSP': r'CISSP[:\s]*([A-Z0-9-]+)?',
            'OSCP': r'OSCP[:\s]*([A-Z0-9-]+)?',
            'CISA': r'CISA[:\s]*([A-Z0-9-]+)?',
            'CISM': r'CISM[:\s]*([A-Z0-9-]+)?',
        }
        certifications = []
        for cname, pattern in cert_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                cert = {'name': cname}
                if matches[0]:
                    cert['verification_id'] = matches[0]
                certifications.append(cert)
        return certifications

    def extract_experience(self, text):
        date_pattern = r'(\d{4})\s*[-–]\s*(\d{4}|present)'
        matches = re.findall(date_pattern, text, re.IGNORECASE)
        total_years = 0
        for start, end in matches:
            try:
                start_year = int(start)
                end_year = datetime.now().year if end.lower() == 'present' else int(end)
                total_years += (end_year - start_year)
            except ValueError:
                continue
        if total_years == 0:
            year_mentions = re.findall(r'(\d+)\+?\s*(?:years|yrs)', text, re.IGNORECASE)
            if year_mentions:
                total_years = float(year_mentions[0])
        return round(total_years, 1)

    def generate_embedding(self, text):
        embedding = self.embedding_model.encode(text[:1000])
        return embedding.tolist()

    def parse_cv(self, file):
        text = self.extract_text_from_cv(file)
        if not text:
            return {'error': 'Could not extract text from file'}

        skills = self.extract_skills(text)
        certifications = self.extract_certifications(text)
        experience_years = self.extract_experience(text)
        entities = self.extract_entities(text)
        embedding = self.generate_embedding(text)

        return {
            'cv_text': text,
            'skills': skills,
            'certifications': certifications,
            'experience_years': experience_years,
            'entities': entities,
            'embedding': embedding,
            'word_count': len(text.split()),
            'certification_count': len(certifications),
        }


_processor = None
_lock = threading.Lock()


def get_bert_processor():
    global _processor
    if _processor is None:
        with _lock:
            if _processor is None:
                _processor = BERTCVProcessor()
    return _processor
