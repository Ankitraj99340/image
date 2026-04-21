import os
import requests
import io
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__, template_folder='../templates')
CORS(app)

# --- API KEY (Yahan apni remove.bg key dalein) ---
REMOVE_BG_API_KEY = "243wBcfWYybSEGmKZTyM9EAz"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return "No image uploaded", 400
            
        file = request.files['image']
        action = request.form.get('action')
        img = Image.open(file.stream)
        
        save_format = 'PNG'
        mimetype = 'image/png'
        download_name = 'processed_image.png'

        # 1. FEATURE: Background Removal (Via API - No Crash)
        if action == 'remove_bg':
            file.stream.seek(0) # File pointer reset
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': file.read()},
                data={'size': 'auto'},
                headers={'X-Api-Key': REMOVE_BG_API_KEY},
            )
            if response.status_code == requests.codes.ok:
                img = Image.open(io.BytesIO(response.content))
            else:
                return f"API Error: {response.text}", 500

        # 2. FEATURE: Professional Enhancement
        elif action == 'enhance':
            if img.mode != 'RGB': img = img.convert('RGB')
            img = ImageEnhance.Contrast(img).enhance(1.4)
            img = ImageEnhance.Sharpness(img).enhance(2.5)
            img = ImageEnhance.Color(img).enhance(1.2)
            img = img.filter(ImageFilter.DETAIL)

        # 3. FEATURE: Resize
        elif action == 'resize':
            w = int(request.form.get('width', 800))
            h = int(request.form.get('height', 800))
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        # 4. FEATURE: Smart Compression
        elif action == 'compress':
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            target_kb = float(request.form.get('target_kb', 100))
            save_format, mimetype = 'JPEG', 'image/jpeg'
            download_name = 'compressed.jpg'
            
            # Binary search logic for perfect compression
            quality = 95
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=quality)
            while img_io.tell() > target_kb * 1024 and quality > 10:
                quality -= 5
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=quality)
            img_io.seek(0)
            return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

        # EXTRA FEATURE: Auto-Fix (Brightness & Sharpness balance)
        if request.form.get('autofix') == 'true':
            img = ImageEnhance.Brightness(img).enhance(1.1)
            img = ImageEnhance.Sharpness(img).enhance(1.5)

        # Final Response
        img_io = io.BytesIO()
        img.save(img_io, format=save_format)
        img_io.seek(0)
        return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

    except Exception as e:
        return str(e), 500