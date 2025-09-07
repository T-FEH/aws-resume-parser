import json
import boto3
import pdfplumber
import docx
import spacy
import re
import os
import io

# Initialize AWS clients with explicit region
s3_client = boto3.client('s3', region_name='eu-north-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_text(file_content, file_ext):
    """Extract text from PDF, TXT, or DOCX file content."""
    ext = file_ext.lower()
    
    if ext == ".pdf":
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)
    elif ext == ".txt":
        text = file_content.decode('utf-8')
    elif ext == ".docx":
        doc = docx.Document(io.BytesIO(file_content))
        text = "\n".join([para.text for para in doc.paragraphs])
    else:
        raise ValueError("Unsupported file type")
    
    # Save extracted text for debugging
    with open("/tmp/extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    return text

def extract_info(text):
    """Extract name, email, phone, skills, education, and generate summary."""
    doc = nlp(text)
    
    # Extract name: First PERSON entity from first 5 lines
    lines = text.split("\n")[:5]
    name = lines[0].strip() if lines else "Unknown"  # Fallback to first line
    for line in lines:
        line_doc = nlp(line)
        for ent in line_doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                break
        if name != "Unknown":
            break
    
    # Extract email
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    email = re.search(email_pattern, text)
    email = email.group(0) if email else "Not found"
    
    # Extract phone number
    phone_pattern = r"(\+?1?[\s-]?(\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}))"
    phone = re.search(phone_pattern, text)
    phone = phone.group(0) if phone else "Not found"
    
    # Extract skills
    skills_keywords = [
        "python", "java", "aws", "sql", "javascript", "cloud", "docker",
        "html", "css", "react", "node", "database", "git"
    ]
    skills = [skill for skill in skills_keywords if skill.lower() in text.lower()]
    
    # Extract education
    education_keywords = [
        "bachelor", "master", "phd", "degree", "university", "college",
        "diploma", "bsc", "msc", "certificate"
    ]
    education = []
    for line in text.split("\n"):
        if any(keyword.lower() in line.lower() for keyword in education_keywords):
            education.append(line.strip())
    education = education if education else ["Not found"]
    
    # Generate summary
    skills_str = ", ".join(skills) if skills else "various areas"
    education_str = education[0] if education and education[0] != "Not found" else "unknown subjects"
    summary = f"{name} has skills in {skills_str} and studied {education_str}."
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "education": education,
        "summary": summary
    }

def save_to_s3(bucket, key, data):
    """Save JSON data to S3."""
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2).encode('utf-8')
    )

def save_to_dynamodb(table_name, data):
    """Save extracted data to DynamoDB."""
    table = dynamodb.Table(table_name)
    table.put_item(Item={
        "email": data["email"],
        "name": data["name"],
        "phone": data["phone"],
        "skills": json.dumps(data["skills"]),
        "education": json.dumps(data["education"]),
        "summary": data["summary"]
    })

def process_s3_file(bucket, key):
    """Process a single S3 file."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()
        file_ext = os.path.splitext(key)[1].lower()
        
        text = extract_text(file_content, file_ext)
        info = extract_info(text)
        
        result_key = key.replace("uploads/", "results/") + ".json"
        save_to_s3(bucket, result_key, info)
        save_to_dynamodb("ResumeData", info)
        
        return {"status": "success", "file": key}
    except Exception as e:
        return {"status": "error", "file": key, "error": str(e)}

def main():
    """Poll S3 for new files and process them."""
    bucket = "resume-parser-tife"
    prefix = "uploads/"
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith(('.pdf', '.txt', '.docx')):
                    result = process_s3_file(bucket, key)
                    print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))

if __name__ == "__main__":
    main()