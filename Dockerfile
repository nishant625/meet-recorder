FROM python:3.11-slim

# Install PortAudio and Chrome dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    portaudio19-dev \
    libasound-dev \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port for Flask
EXPOSE 10000

# Run the application
CMD ["python", "main.py"]
