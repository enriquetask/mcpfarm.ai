FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp uvicorn

COPY server.py .

EXPOSE 9001

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost',9001)); s.close()" || exit 1

CMD ["python", "server.py"]
