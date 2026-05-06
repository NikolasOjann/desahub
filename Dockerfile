# Gunakan base image Python versi ringan
FROM python:3.9-slim

# Set working directory di dalam container
WORKDIR /app

# Copy file requirements terlebih dahulu untuk caching layer Docker
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code aplikasi ke dalam container
COPY . .

# Expose port yang akan digunakan oleh FastAPI (8000)
EXPOSE 8000

# Perintah untuk menjalankan aplikasi menggunakan Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]