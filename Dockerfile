# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the outside world
EXPOSE 8000

# Define the command to run the application using Uvicorn
# 'backend:app' means look for the 'app' object in 'backend.py'
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]