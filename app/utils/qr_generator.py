# app/utils/qr_generator.py
import qrcode
import os

def generate_qr(data, path):
    # Make sure the directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Create QR code image
    img = qrcode.make(data)

    # Save image to file
    img.save(path)
