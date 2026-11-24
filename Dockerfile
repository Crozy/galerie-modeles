FROM python:3.12-slim
WORKDIR /app
COPY server.py .
COPY static ./static
ENV MODELS_DIR=/models PORT=8090 PYTHONUNBUFFERED=1
EXPOSE 8090
USER nobody
CMD ["python", "server.py"]
