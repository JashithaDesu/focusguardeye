FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY reports/ ./reports/
COPY storage/ ./storage/
COPY app/app.py .
RUN mkdir -p /data
ENV FOCUSGUARD_DB_PATH=/data/focusguard.db
EXPOSE 5000
CMD ["python", "app.py"]