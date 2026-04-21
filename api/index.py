import os
import requests
import io
import base64
import time
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__, template_folder='../templates')
CORS(app)

# --- API KEYS (Yahan apni keys dalein) ---
REMOVE_BG_API_KEY = "243wBcfWYybSEGmKZTyM9EAz"
REPLICATE_API_TOKEN = "r8_GTioDnQH7DEzPwup7zwTFftk9XyK7JS2RvL73"

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

        # --- 1. AI BACKGROUND REMOVAL ---
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
            else:
                return f"BG API Error: {response.text}", 500

        # --- 2. REMINI-STYLE AI ENHANCEMENT (GFPGAN) ---
   elif action == 'enhance':
            # 1. Photo ko resize karo taaki AI fast chale (Remini bhi yahi karta hai)
            # 800px width par quality achi aayegi aur speed 3x badh jayegi
            img.thumbnail((800, 800)) 
            
            # ... (Base64 conversion code) ...

            # 2. Replicate API request (Wait logic ko thoda relax karo)
            start_time = time.time()
            while True:
                # Agar 50 second ho gaye, toh loop tod do (Vercel crash se pehle)
                if time.time() - start_time > 50:
                    return "AI processing took too long. Try a smaller image.", 504
                
                res_check = requests.get(f"https://api.replicate.com/v1/predictions/{predict_id}", headers=headers)
                data = res_check.json()
                status = data.get('status')
                
                if status == "succeeded":
                    img_res = requests.get(data['output'])
                    img = Image.open(io.BytesIO(img_res.content))
                    break
                elif status == "failed":
                    return "AI Generation Error", 500
                
                # 3 second ka gap taaki connection baar-baar reset na ho
                time.sleep(3)

        # --- 3. RESIZE ---
        elif action == 'resize':
            w = int(request.form.get('width', 800))
            h = int(request.form.get('height', 800))
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        # --- 4. SMART COMPRESSION ---
        elif action == 'compress':
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            target_kb = float(request.form.get('target_kb', 100))
            save_format, mimetype = 'JPEG', 'image/jpeg'
            download_name = 'compressed.jpg'
            
            quality = 95
            img_io = io.BytesIO()
            while quality > 10:
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=quality, optimize=True)
                if img_io.tell() <= target_kb * 1024:
                    break
                quality -= 5
            img_io.seek(0)
            return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

        # Final Save Logic (Size control)
        img_io = io.BytesIO()
        if save_format == 'PNG':
            img.save(img_io, format='PNG', optimize=True)
        else:
            img.save(img_io, format='JPEG', quality=85, optimize=True)
            
        img_io.seek(0)
        return send_file(img_io, mimetype=mimetype, as_attachment=True, download_name=download_name)

    except Exception as e:
        return str(e), 500

#if __name__ == '__main__':
   # app.run(debug=True, port=5000)
