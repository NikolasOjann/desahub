import os
import pymysql
import boto3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'desahub_rahasia_aman'

# ==========================================
# KONFIGURASI DATABASE (MENGGUNAKAN SATU SUMBER)
# ==========================================
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASS = os.environ.get("DB_PASSWORD") # Pastikan nama variabel sesuai di ECS
DB_NAME = "desahub_db"

def get_db_connection():
    # Koneksi awal ke server MySQL (Tanpa database spesifik)
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    # Pastikan database ada, baru kemudian digunakan
    cursor.execute("CREATE DATABASE IF NOT EXISTS desahub_db")
    cursor.execute("USE desahub_db")
    
    # Pastikan tabel juga tersedia
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengajuan (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nik VARCHAR(20),
            nama VARCHAR(100),
            jenis_surat VARCHAR(50),
            keperluan TEXT,
            dokumen_url VARCHAR(255),
            status VARCHAR(50) DEFAULT 'Menunggu Verifikasi',
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# ==========================================
# KONFIGURASI AWS S3 & CLOUDFRONT
# ==========================================
S3_BUCKET = os.environ.get("S3_BUCKET")
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN")

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"
)

def upload_to_s3(file_obj):
    if file_obj and file_obj.filename != '':
        filename = secure_filename(file_obj.filename)
        try:
            s3_client.upload_fileobj(
                file_obj, S3_BUCKET, filename,
                ExtraArgs={"ContentType": file_obj.content_type}
            )
            # RETURN LINK CLOUDFRONT (Syarat Mutlak ETS 2)
            return f"https://{CLOUDFRONT_DOMAIN}/{filename}"
        except Exception as e:
            print("Error S3:", e)
            return None
    return None

# ==========================================
# ROUTES (HALAMAN WEB)
# ==========================================
@app.route('/')
def index():
    return "<h1>Selamat Datang di DesaHub</h1><p>Silakan ke <a href='/ajukan'>/ajukan</a> untuk membuat surat.</p>"

@app.route('/ajukan', methods=['GET', 'POST'])
def ajukan():
    if request.method == 'POST':
        # ... (Biarkan kode proses POST / S3 / RDS tetap sama seperti sebelumnya) ...
        # Contoh respons sukses jika berhasil:
        if dokumen_url:
            # ... proses insert DB ...
            return f"""
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h2 style="color:green;">Pengajuan Berhasil! 🎉</h2>
                <p>Dokumen Anda: <a href='{dokumen_url}'>Lihat di CloudFront</a></p>
                <br><a href='/tracking' style="padding:10px 20px; background:blue; color:white; text-decoration:none; border-radius:5px;">Cek Status Layanan</a>
            </div>
            """
        else:
            return "Gagal upload dokumen ke S3."

    # MENGGUNAKAN RENDER TEMPLATE SEKARANG!
    return render_template('ajukan.html')

@app.route('/tracking')
def tracking():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Mengambil data terbaru di atas
        cursor.execute("SELECT * FROM pengajuan ORDER BY id DESC")
        data = cursor.fetchall()
    conn.close()
    
    # Render template dan kirim variabel 'data' ke HTML
    return render_template('tracking.html', data=data)

if __name__ == '__main__':
    # Inisialisasi DB sekali saat start
    get_db_connection().close()
    app.run(host='0.0.0.0', port=5000)