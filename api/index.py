import os
import requests
import io
import cv2
import numpy as np 
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__, template_folder='../templates')
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

        # Ensure image is in RGB for processing
        if img.mode != 'RGB' and action != 'remove_bg':
            img = img.convert('RGB')

        # --- 1. FEATURE: Background Removal (Wahi Same Logic) ---
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

        # --- 2. FEATURE: Professional Enhancement (New Natural Logic) ---
        elif action == 'enhance':
            # Step 1: Subtle Upscaling (1.5x quality ke liye)
            w, h = img.size
            img = img.resize((int(w * 1.5), int(h * 1.5)), Image.Resampling.LANCZOS)
            
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Step 2: Bilateral Filtering (Natural Smoothing)
            # fastNlMeans ki jagah ye use kiya hai taaki chehra 'harsh' na dikhe
            img_cv = cv2.bilateralFilter(img_cv, d=5, sigmaColor=35, sigmaSpace=35)

            # Step 3: CLAHE (Natural Contrast)
            lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(4,4))
            l = clahe.apply(l)
            img_cv = cv2.merge((l, a, b))
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_LAB2BGR)

            # Step 4: Back to PIL
            img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))

            # Step 5: Smart Sharpening (Soft edges)
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=100, threshold=3))
            
            # Step 6: Final Polish
            img = ImageEnhance.Color(img).enhance(1.15)
            img = ImageEnhance.Contrast(img).enhance(1.05)
            download_name = 'enhanced.png'

        # --- 3. FEATURE: Resize (Wahi Same Logic) ---
        elif action == 'resize':
            w = int(request.form.get('width', 800))
            h = int(request.form.get('height', 800))
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        # --- 4. FEATURE: Smart Compression (Wahi Same Logic) ---
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

        # --- EXTRA FEATURE: Auto-Fix ---
        if request.form.get('autofix') == 'true':
            img = ImageEnhance.Brightness(img).enhance(1.1)
            img = ImageEnhance.Sharpness(img).enhance(1.5)

        # Final Response
        img_io = io.BytesIO()
        img.save(img_io, format=save_format)
        img_io.seek(0)
        return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

    except Exception as e:
        return f"Server Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
