FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Playwright browsers are installed
RUN playwright install chromium

# Copy the rest of the application code
COPY . .

# Create reports directory and ensure it's writable
RUN mkdir -p reports && chmod 777 reports

# Set default environment variables
ENV BASE_URL=http://host.docker.internal:3000
ENV HEADLESS=true
ENV REPORTS_DIR=/app/reports

# Default command to run tests with verbose output
CMD ["pytest", "tests/", "-v", "-s", "--tb=short"]
