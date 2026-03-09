FROM python:3.11-slim

WORKDIR /app

# Install Chromium, ChromeDriver, and Xvfb (virtual display for pyautogui)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Environment for cloud/headless Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV RAILWAY_ENVIRONMENT=production
ENV DISPLAY=:99

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE 5000
# Start virtual display for pyautogui, then run app
CMD Xvfb :99 -screen 0 1024x768x24 & export DISPLAY=:99 && gunicorn -b 0.0.0.0:$PORT app:app
