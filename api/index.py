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
REMOVE_BG_API_KEY = "YOUR_REMOVE_BG_KEY"
REPLICATE_API_TOKEN = "YOUR_REPLICATE_TOKEN"

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
            # Image ko Base64 mein convert karna
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            img_data_uri = f"data:image/jpeg;base64,{img_str}"

            headers = {
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "version": "7de2ea1114d03d9f344863e2a95c944487f3b610c21342c366472477382221b6",
                "input": {"img": img_data_uri, "upscale": 2}
            }

            # Start AI Prediction
            res_start = requests.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
            if res_start.status_code != 201:
                return f"AI API Error: {res_start.text}", 500
            
            predict_id = res_start.json()['id']
            # Loop jab tak AI process na ho jaye
            while True:
                res_check = requests.get(f"https://api.replicate.com/v1/predictions/{predict_id}", headers=headers)
                status = res_check.json()['status']
                if status == "succeeded":
                    output_url = res_check.json()['output']
                    img_res = requests.get(output_url)
                    img = Image.open(io.BytesIO(img_res.content))
                    break
                elif status == "failed":
                    return "AI Restoration Failed", 500
                time.sleep(1) # 1 second wait karein

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
