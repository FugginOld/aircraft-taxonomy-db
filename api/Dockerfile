FROM python:3.10.17-slim

WORKDIR /app

# Install API dependencies.
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API application code.
COPY api/main.py ./main.py

# The data/ directory is expected to be bind-mounted at runtime so that the
# API always reflects the latest CSV files without requiring a rebuild.
# Falls back to /app/data if no mount is provided (useful for testing).
ENV DATA_DIR=/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
