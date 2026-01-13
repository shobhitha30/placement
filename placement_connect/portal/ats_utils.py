"""ATS (Applicant Tracking System) utilities for resume scoring."""

from pdfminer.high_level import extract_text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


def extract_text_from_pdf(pdf_path):
    """Extracts raw text from an uploaded PDF file."""
    try:
        return extract_text(pdf_path)
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""


def calculate_ats_score(resume_text, job_description):
    """Calculates a percentage match between resume and job description."""
    if not resume_text or not job_description:
        return 0.0
    
    content = [resume_text, job_description]
    cv = TfidfVectorizer(stop_words='english')
    count_matrix = cv.fit_transform(content)
    
    # Calculate Cosine Similarity
    similarity_matrix = cosine_similarity(count_matrix)
    match_percentage = similarity_matrix[0][1] * 100
    return round(match_percentage, 2)