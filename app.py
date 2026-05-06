import os
import pymysql
import boto3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'desahub_rahasia_aman'

# ==========================================
# KONFIGURASI DATABASE (AWS RDS)
# ==========================================
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASS = os.environ.get("DB_PASS", "admin123")
DB_NAME = os.environ.get("DB_NAME", "desahub_db")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# ==========================================
# KONFIGURASI AWS S3 & CLOUDFRONT
# ==========================================
S3_BUCKET = os.environ.get("S3_BUCKET", "desahub-bucket-anda")
# WAJIB ETS 2: Konten statis diakses melalui CloudFront
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "d123456789.cloudfront.net")

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
            # RETURN LINK CLOUDFRONT (Sesuai syarat ETS)
            return f"https://{CLOUDFRONT_DOMAIN}/{filename}"
        except Exception as e:
            print("Error S3:", e)
            return None
    return None

# ==========================================
# INISIALISASI DATABASE OTOMATIS
# ==========================================
def init_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Tabel Pengajuan Surat
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pengajuan (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nik VARCHAR(20),
                    nama VARCHAR(100),
                    jenis_surat VARCHAR(50),
                    keperluan TEXT,
                    dokumen_url VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'Menunggu Verifikasi'
                )
            """)
        conn.commit()
        conn.close()
        print("Database DesaHub siap!")
    except Exception as e:
        print("Gagal inisialisasi database:", e)

init_db()

# ==========================================
# ROUTES (HALAMAN WEB)
# ==========================================
@app.route('/')
def index():
    return "<h1>Selamat Datang di DesaHub</h1><p>Silakan ke /ajukan untuk membuat surat.</p>"

@app.route('/ajukan', methods=['GET', 'POST'])
def ajukan():
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        jenis = request.form['jenis_surat']
        keperluan = request.form['keperluan']
        file_ktp = request.files['file_ktp']
        
        # Upload file ke S3, dapatkan link CloudFront
        dokumen_url = upload_to_s3(file_ktp)
        
        if dokumen_url:
            # Simpan ke RDS
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pengajuan (nik, nama, jenis_surat, keperluan, dokumen_url) VALUES (%s, %s, %s, %s, %s)",
                    (nik, nama, jenis, keperluan, dokumen_url)
                )
            conn.commit()
            conn.close()
            return f"Pengajuan berhasil! Dokumen tersimpan di: <a href='{dokumen_url}'>Lihat Dokumen</a>"
        else:
            return "Gagal upload dokumen."

    # Tampilan Form HTML Sederhana
    form_html = """
    <h2>Pengajuan Surat Administrasi DesaHub</h2>
    <form method="POST" enctype="multipart/form-data">
        NIK: <input type="text" name="nik" required><br><br>
        Nama: <input type="text" name="nama" required><br><br>
        Jenis Surat: <select name="jenis_surat">
            <option value="Surat Domisili">Surat Domisili</option>
            <option value="Surat Keterangan Usaha">Surat Keterangan Usaha</option>
        </select><br><br>
        Keperluan: <textarea name="keperluan"></textarea><br><br>
        Upload KTP (Gambar/PDF): <input type="file" name="file_ktp" required><br><br>
        <button type="submit">Ajukan Surat</button>
    </form>
    <br><a href='/tracking'>Cek Status Pengajuan</a>
    """
    return form_html

@app.route('/tracking')
def tracking():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM pengajuan ORDER BY id DESC")
        data = cursor.fetchall()
    conn.close()
    
    html = "<h2>Tracking Status Layanan</h2><table border='1'><tr><th>ID</th><th>Nama</th><th>Surat</th><th>Status</th><th>Dokumen (CloudFront)</th></tr>"
    for row in data:
        html += f"<tr><td>{row['id']}</td><td>{row['nama']}</td><td>{row['jenis_surat']}</td><td><b>{row['status']}</b></td><td><a href='{row['dokumen_url']}' target='_blank'>Lihat File</a></td></tr>"
    html += "</table><br><a href='/ajukan'>Kembali</a>"
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)