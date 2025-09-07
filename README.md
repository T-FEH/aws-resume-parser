# AWS Resume Parser
A Python-based resume parser hosted on AWS EC2, using Flask, S3, and DynamoDB. Uploads PDF/TXT/DOCX resumes, extracts name, email, phone, skills, and education, and saves results to S3 and DynamoDB.

## Features
- Web UI for resume uploads
- Extracts data using spaCy and regex
- Stores results in S3 and DynamoDB
- Styled UI with Flask

## Setup
1. Launch an EC2 t2.micro instance (Amazon Linux 2023).
2. Install dependencies: `pip install -r requirements.txt`.
3. Run: `nohup python -u app.py &`.
4. Access at `http://<ec2-public-ip>:5000`.

## AWS Resources
- S3: `resume-parser-tife`
- DynamoDB: `ResumeData`
- EC2: t2.micro with IAM role (`resume-parser-ec2-role`)

## Free Tier
Uses AWS Free Tier (750 EC2 hours, 5GB S3, 25GB DynamoDB).
