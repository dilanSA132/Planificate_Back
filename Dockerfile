FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

EXPOSE 8000

CMD ["/wait-for-db.sh", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
