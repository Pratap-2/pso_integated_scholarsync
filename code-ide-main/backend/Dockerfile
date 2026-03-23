# Use an official Python multi-architecture slim image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - g++ is required for compiling C++ code
# - build-essential provides additional tools just in case
RUN apt-get update && apt-get install -y \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the FastApi application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
