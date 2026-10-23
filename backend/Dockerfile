FROM python:3.12.10-slim

WORKDIR /workspace
COPY requirements-repro.lock /workspace/requirements-repro.lock
RUN python -m pip install --no-cache-dir -r requirements-repro.lock
COPY backend /workspace/backend
COPY research /workspace/research
COPY docs/EMS_incident_dispatch_data_description.csv /workspace/docs/EMS_incident_dispatch_data_description.csv

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
