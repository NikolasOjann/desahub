# Gunakan image Python yang ringan
FROM python:3.9-slim

# Tentukan direktori kerja di dalam kontainer
WORKDIR /app

# Install pustaka sistem yang diperlukan untuk koneksi MySQL
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode aplikasi
COPY . .

# Ekspos port Flask
EXPOSE 5000

# Perintah menjalankan aplikasi saat kontainer ECS menyala
CMD ["python", "app.py"]