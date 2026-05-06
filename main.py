from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import boto3
import os
from sqlalchemy import create_engine

app = FastAPI(title="DesaHub API")

# --- KONFIGURASI AWS & DATABASE ---
# Catatan: Nanti di ECS, value ini sebaiknya diambil dari Environment Variables (Parameter Store/Secrets Manager)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "desahub-bucket-nama-anda")
CLOUDFRONT_URL = os.getenv("CLOUDFRONT_URL", "https://d123456789.cloudfront.net")
DB_URL = os.getenv("DB_URL", "mysql+pymysql://admin:password@nama-rds-endpoint.aws.com:3306/desahub_db")

# Setup Boto3 Client untuk S3
s3_client = boto3.client('s3')

# Setup Database Engine (Koneksi ke RDS)
# engine = create_engine(DB_URL) # Hilangkan komentar ini saat RDS sudah siap

# --- FITUR 1: Autentikasi/Login Warga (Mockup) ---
@app.post("/login")
def login_warga(nik: str = Form(...), password: str = Form(...)):
    # Di sini nanti Anda buat logika query ke DB (RDS) untuk cek user
    if nik == "123456" and password == "rahasia":
        return {"status": "success", "message": "Login berhasil"}
    raise HTTPException(status_code=401, detail="NIK atau Password salah")

# --- FITUR 2 & FITUR WAJIB S3: Pengajuan Surat & Upload Dokumen ---
@app.post("/pengajuan-surat")
async def ajukan_surat(
    jenis_surat: str = Form(...),
    nik: str = Form(...),
    dokumen_ktp: UploadFile = File(...) # Fitur Upload
):
    try:
        # 1. Baca file yang diupload
        file_content = await dokumen_ktp.read()
        file_name = f"dokumen/{nik}_{dokumen_ktp.filename}"
        
        # 2. Upload ke Amazon S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=file_content,
            ContentType=dokumen_ktp.content_type
        )
        
        # 3. Buat URL CloudFront untuk file tersebut (Sesuai Aturan: Akses file WAJIB via CDN)
        file_url = f"{CLOUDFRONT_URL}/{file_name}"
        
        # 4. Simpan data pengajuan & file_url ke Amazon RDS
        # (Tambahkan logika SQLAlchemy INSERT ke DB di sini)
        
        return {
            "status": "success", 
            "message": "Pengajuan berhasil disimpan",
            "berkas_url": file_url # URL ini menggunakan CloudFront, BUKAN S3 langsung
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- FITUR 3: Tracking Status Layanan ---
@app.get("/tracking/{nik}")
def cek_status(nik: str):
    # Logika query ke RDS untuk cek status pengajuan berdasarkan NIK
    # Mockup response:
    return {
        "nik": nik,
        "status_pengajuan": "Sedang Diproses oleh Kepala Desa",
        "estimasi_selesai": "2 Hari Kerja"
    }

@app.get("/")
def health_check():
    return {"message": "DesaHub API Berjalan Normal di ECS"}