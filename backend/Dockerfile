FROM python:3.11.4-buster

# Set working directory
WORKDIR /app

# Install necessary packages
RUN apt-get update && apt-get install -y \
    gnupg \
    curl \
    build-essential \
    software-properties-common \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose the port on which the app will run
EXPOSE 8000

# Uncomment this line if you want to add a health check
# HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
# ENTRYPOINT ["uvicorn"]

# Run the application
CMD ["fastapi", "run", "main.py", "--port", "8000"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
