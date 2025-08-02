# Használj hivatalos Python image-et
FROM python:3.11-slim

# Munkakönyvtár beállítása
WORKDIR /app

# Követelmények bemásolása és telepítése
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App bemásolása
COPY . .

# Port beállítása (Dash default: 8050)
EXPOSE 8050

# Indítás Gunicorn-nal (ajánlott Renderen)
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "app:server"]