FROM python:3.11-slim
WORKDIR /app

# The deltasci package, bundled by ./bundle.sh (pyproject.toml + src/) so the build is
# self-contained and carries the current source (coverage + title-resolution included).
COPY pkg /app/pkg
RUN pip install --no-cache-dir ./pkg "fastapi>=0.110" "uvicorn[standard]>=0.29"

COPY app.py /app/app.py

# Hugging Face Spaces route to this port.
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
