# app/utils/qr_generator.py
import qrcode

def generate_qr(data, filename, size=300):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size))
    img.save(filename)