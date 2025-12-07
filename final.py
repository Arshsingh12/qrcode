from flask import Flask, request, send_file, render_template_string
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os
from uuid import uuid4

app = Flask(__name__)

# Fixed values
FIXED_UPI_ID = "7840030011@ptsbi"
FIXED_NAME = "Arshdeep Singh Gill"
FIXED_LOGO_PATH = "arsh.jpg"  # Ensure this file exists in the same directory

# HTML template for the form and QR code display
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPI Payment QR Code Generator</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; text-align: center; }
        .container { display: flex; flex-direction: column; align-items: center; }
        input, button { margin: 10px; padding: 8px; width: 300px; }
        button { background-color: green; color: white; border: none; cursor: pointer; }
        button:hover { background-color: darkgreen; }
        img { max-width: 300px; margin-top: 20px; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>UPI Payment QR Code Generator</h1>
    <div class="container">
        <form method="POST" action="/">
            <label for="amount">Amount (₹):</label><br>
            <input type="number" id="amount" name="amount" step="0.01" required><br>
            <label for="note">Note / Purpose (optional):</label><br>
            <input type="text" id="note" name="note"><br>
            <button type="submit">Generate QR Code</button>
        </form>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
        {% if qr_url %}
            <img src="{{ qr_url }}" alt="QR Code">
            <br>
            <a href="{{ qr_url }}" download="qr_{{ filename }}.png">
                <button>Download QR Code</button>
            </a>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    qr_url = None
    filename = None

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        note = request.form.get("note", "").strip()

        if not amount:
            error = "Please enter an amount."
        else:
            try:
                # Build UPI URL
                upi_url = f"upi://pay?pa={FIXED_UPI_ID}&pn={FIXED_NAME}&am={amount}&cu=INR"

                # Generate QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(upi_url)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

                # Add logo
                if os.path.exists(FIXED_LOGO_PATH):
                    try:
                        logo = Image.open(FIXED_LOGO_PATH)
                        logo = logo.resize((220, 220), Image.LANCZOS)
                        pos = ((qr_img.size[0] - 220) // 2, (qr_img.size[1] - 220) // 2)
                        qr_img.paste(logo, pos)
                    except Exception as e:
                        error = f"Could not use logo: {e}"

                # Labels
                label_line1 = f"Pay ₹{amount} to {FIXED_NAME}"
                label_line2 = note if note else ""

                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    try:
                        font = ImageFont.truetype("DejaVuSans.ttf", 20)
                    except:
                        font = ImageFont.load_default()

                draw_temp = ImageDraw.Draw(qr_img)
                bbox1 = draw_temp.textbbox((0, 0), label_line1, font=font)
                bbox2 = draw_temp.textbbox((0, 0), label_line2, font=font)

                text1_w = bbox1[2] - bbox1[0]
                text1_h = bbox1[3] - bbox1[1]
                text2_w = bbox2[2] - bbox2[0]
                text2_h = bbox2[3] - bbox2[1]

                label_height = text1_h + (text2_h if label_line2 else 0) + 20
                final_img = Image.new("RGB", (qr_img.width, qr_img.height + label_height), "white")
                final_img.paste(qr_img, (0, 0))

                draw_final = ImageDraw.Draw(final_img)
                draw_final.text(((qr_img.width - text1_w) // 2, qr_img.height + 5), label_line1, fill="black", font=font)
                if label_line2:
                    draw_final.text(((qr_img.width - text2_w) // 2, qr_img.height + text1_h + 10), label_line2, fill="gray", font=font)

                # Save QR code to bytes
                img_io = io.BytesIO()
                final_img.save(img_io, format="PNG")
                img_io.seek(0)

                # Generate unique filename for URL
                filename = f"qr_{FIXED_NAME.replace(' ', '_')}_{amount}"
                qr_url = f"/qr/{uuid4().hex}.png"

                # Store image in memory (in production, consider a more robust storage solution)
                app.qr_images = getattr(app, 'qr_images', {})
                app.qr_images[qr_url] = img_io.getvalue()

            except Exception as e:
                error = f"Error generating QR code: {e}"

    return render_template_string(HTML_TEMPLATE, error=error, qr_url=qr_url, filename=filename)

@app.route("/qr/<image_id>")
def serve_qr(image_id):
    qr_url = f"/qr/{image_id}"
    if hasattr(app, 'qr_images') and qr_url in app.qr_images:
        return send_file(
            io.BytesIO(app.qr_images[qr_url]),
            mimetype="image/png",
            as_attachment=False
        )
    return "Image not found", 404

if __name__ == "__main__":
    # For development only; production will use Gunicorn
    app.run(host="0.0.0.0", port=5000, debug=False)