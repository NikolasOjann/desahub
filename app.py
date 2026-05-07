import os
import pymysql
import boto3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'desahub_rahasia_aman'

# ==========================================
# KONFIGURASI DATABASE
# ==========================================
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASS = os.environ.get("DB_PASSWORD")
DB_NAME = "desahub_db"

def get_db_connection():
    conn = pymysql.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS desahub_db")
    cursor.execute("USE desahub_db")
    
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
    # Menampilkan halaman utama
    return render_template('index.html')

@app.route('/ajukan', methods=['GET', 'POST'])
def ajukan():
    if request.method == 'POST':
        # 1. Ambil data dari form HTML
        nik = request.form['nik']
        nama = request.form['nama']
        jenis = request.form['jenis_surat']
        keperluan = request.form['keperluan']
        file_ktp = request.files['file_ktp']
        
        # 2. Upload file ke S3
        dokumen_url = upload_to_s3(file_ktp)
        
        if dokumen_url:
            # 3. Simpan ke Database RDS
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pengajuan (nik, nama, jenis_surat, keperluan, dokumen_url) VALUES (%s, %s, %s, %s, %s)",
                    (nik, nama, jenis, keperluan, dokumen_url)
                )
            conn.commit()
            conn.close()
            
            # 4. Tampilkan pesan sukses
            return f"""
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h2 style="color:green;">Pengajuan Berhasil! 🎉</h2>
                <p>Dokumen Anda: <a href='{dokumen_url}'>Lihat di CloudFront</a></p>
                <br><a href='/tracking' style="padding:10px 20px; background:#0d6efd; color:white; text-decoration:none; border-radius:5px;">Cek Status Layanan</a>
            </div>
            """
        else:
            return "Gagal upload dokumen ke S3."

    # Menampilkan form jika method-nya GET
    return render_template('ajukan.html')

@app.route('/tracking')
def tracking():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM pengajuan ORDER BY id DESC")
        data = cursor.fetchall()
    conn.close()
    
    return render_template('tracking.html', data=data)

if __name__ == '__main__':
    get_db_connection().close()
    app.run(host='0.0.0.0', port=5000)