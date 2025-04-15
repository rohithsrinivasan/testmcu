# Use an official Python image
FROM python:3.11-slim

# Install Java (required for some libraries like tabula-py, pySpark, etc.)
RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Run Streamlit
CMD ["streamlit", "run", "interface.py", "--server.port=$PORT", "--server.address=0.0.0.0"]