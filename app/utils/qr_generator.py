# app/utils/qr_generator.py
import qrcode
import os

def generate_qr(url: str, save_path: str):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    img = qrcode.make(url)
    img.save(save_path)