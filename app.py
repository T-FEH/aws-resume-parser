from flask import Flask, request, render_template_string, jsonify
import logging
import boto3
import os
from parser import extract_text, extract_info, save_to_s3, save_to_dynamodb

app = Flask(__name__)

# Initialize boto3 clients
s3_client = boto3.client('s3', region_name='eu-north-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-north-1')
bucket = "resume-parser-tife"

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# HTML template for UI
UI_TEMPLATE = """
<html>
<head>
  <title>Resume Parser</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1, h2 { color: #333; }
    p { margin: 10px 0; }
    form { margin-bottom: 20px; }
    input[type=file], input[type=submit] { margin: 10px 0; }
    .summary { background-color: #f9f9f9; padding: 15px; border-radius: 5px; }
  </style>
</head>
<body>
  <h1>Upload Resume</h1>
  <form method="POST" enctype="multipart/form-data">
    <input type="file" name="resume" accept=".pdf,.txt,.docx">
    <input type="submit" value="Parse">
  </form>
  {% if summary %}
    <h2>Parsed Summary</h2>
    <div class="summary">
      <p><b>Name:</b> {{ summary.name }}</p>
      <p><b>Email:</b> {{ summary.email }}</p>
      <p><b>Phone:</b> {{ summary.phone }}</p>
      <p><b>Skills:</b> {{ summary.skills | join(', ') }}</p>
      <p><b>Education:</b> {{ summary.education | join('; ') }}</p>
      <p><b>Summary:</b> {{ summary.summary }}</p>
    </div>
  {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'resume' not in request.files:
            logging.error("No file uploaded")
            return jsonify({"error": "No file uploaded"})
        
        file = request.files['resume']
        if file.filename == '':
            logging.error("No selected file")
            return jsonify({"error": "No selected file"})
        
        logging.info(f"Uploaded file: {file.filename}")
        
        file_content = file.read()
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        try:
            text = extract_text(file_content, file_ext)
            logging.info("Text extracted successfully")
            info = extract_info(text)
            logging.info("Info extracted successfully")
            
            # Save to S3
            result_key = f"results/{file.filename}.json"
            save_to_s3(bucket, result_key, info)
            logging.info(f"Saved to S3: {result_key}")
            
            # Save to DynamoDB
            save_to_dynamodb("ResumeData", info)
            logging.info("Saved to DynamoDB")
            
            return render_template_string(UI_TEMPLATE, summary=info)
        except Exception as e:
            logging.error(f"Error parsing file: {str(e)}")
            return jsonify({"error": str(e)})
    
    return render_template_string(UI_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
