import os
import requests
import io
import cv2
import numpy as np 
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter

# Path settings for Render/Vercel
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '..', 'templates')

app = Flask(__name__, template_folder=template_dir)
CORS(app)

# --- API KEY ---
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
        
        # Default settings
        save_format = 'PNG'
        mimetype = 'image/png'
        download_name = 'processed_image.png'

        # Ensure image is in RGB
        if img.mode != 'RGB' and action != 'remove_bg':
            img = img.convert('RGB')

        # --- 1. Background Removal ---
        if action == 'remove_bg':
            file.stream.seek(0) 
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': file.read()},
                data={'size': 'auto'},
                headers={'X-Api-Key': REMOVE_BG_API_KEY},
            )
            if response.status_code == requests.codes.ok:
                img = Image.open(io.BytesIO(response.content))
                download_name = 'no_bg.png'
            else:
                return f"API Error: {response.text}", 500

        # --- 2. Professional Enhancement ---
        elif action == 'enhance':
            w, h = img.size
            img = img.resize((int(w * 1.5), int(h * 1.5)), Image.Resampling.LANCZOS)
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            img_cv = cv2.bilateralFilter(img_cv, d=5, sigmaColor=35, sigmaSpace=35)
            lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(4,4))
            l = clahe.apply(l)
            img_cv = cv2.merge((l, a, b))
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_LAB2BGR)
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=100, threshold=3))
            img = ImageEnhance.Color(img).enhance(1.15)
            img = ImageEnhance.Contrast(img).enhance(1.05)
            download_name = 'enhanced.png'

        # --- 3. Resize ---
        elif action == 'resize':
            w = int(request.form.get('width', 800))
            h = int(request.form.get('height', 800))
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        # --- 4. Smart Compression ---
        elif action == 'compress':
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            target_kb = float(request.form.get('target_kb', 100))
            save_format, mimetype = 'JPEG', 'image/jpeg'
            download_name = 'compressed.jpg'
            quality = 95
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=quality)
            while img_io.tell() > target_kb * 1024 and quality > 10:
                quality -= 5
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=quality)
            img_io.seek(0)
            return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

        # Final Response
        img_io = io.BytesIO()
        img.save(img_io, format=save_format)
        img_io.seek(0)
        return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

    except Exception as e:
        return f"Server Error: {str(e)}", 500

# Bilkul left side se shuru (Indentation Fix)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
