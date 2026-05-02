FROM python:3.13-slim

WORKDIR /app

# ── Dépendances système ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    curl \
    wget \
    unzip \
    openjdk-17-jre-headless \
    nodejs \
    npm \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# ── Docker CLI (pour les scanners DinD : gosec, brakeman, psalm, etc.) ─────
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# ── Trivy (container & SCA scanner) ───────────────────────────────────────
RUN wget -qO- https://github.com/aquasecurity/trivy/releases/download/v0.51.1/trivy_0.51.1_Linux-64bit.tar.gz \
    | tar -xz -C /usr/local/bin trivy

# ── OWASP Dependency-Check ─────────────────────────────────────────────────
RUN wget -q https://github.com/jeremylong/DependencyCheck/releases/download/v9.2.0/dependency-check-9.2.0-release.zip \
    -O /tmp/dependency-check.zip \
    && unzip -q /tmp/dependency-check.zip -d /opt/ \
    && rm /tmp/dependency-check.zip \
    && ln -s /opt/dependency-check/bin/dependency-check.sh /usr/local/bin/dependency-check

# ── ESLint (JS/TS SAST) ────────────────────────────────────────────────────
RUN npm install -g eslint @eslint/js

# ── Dépendances Python ─────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── bandit & semgrep (installés via pip) ──────────────────────────────────
RUN pip install --no-cache-dir bandit semgrep

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
