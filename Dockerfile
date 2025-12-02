# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies first (this layer will be cached)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        wget \
        unzip \
        sudo \
        build-essential \
        ca-certificates \
        gnupg \
        lsb-release \
        python3-dev \
        python3-venv \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        libffi-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        liblzma-dev \
        procps \
        psmisc \
        findutils \
        grep \
        coreutils \
        gawk \
        sed \
        tar \
        gzip \
        bzip2 \
        xz-utils \
        file \
        tree \
        jq \
        less \
    && rm -rf /var/lib/apt/lists/*

# Install Java 21 from Eclipse Temurin
RUN wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null && \
    echo "deb https://packages.adoptium.net/artifactory/deb $(awk -F= '/^VERSION_CODENAME/{print$2}' /etc/os-release) main" | tee /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y temurin-21-jdk maven && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Gradle
RUN wget -q https://services.gradle.org/distributions/gradle-8.10.2-bin.zip -O /tmp/gradle.zip && \
    unzip -q /tmp/gradle.zip -d /opt/ && \
    ln -s /opt/gradle-8.10.2/bin/gradle /usr/local/bin/gradle && \
    rm /tmp/gradle.zip

# Set JAVA_HOME for Temurin JDK 21
ENV JAVA_HOME=/usr/lib/jvm/temurin-21-jdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

# Install Auggie CLI
RUN npm install -g @augmentcode/auggie

# Upgrade pip and install Python package management tools
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir pipx virtualenv poetry && \
    pipx ensurepath

# Copy project files for installation
COPY pyproject.toml .
COPY MANIFEST.in .
COPY cyoda_mcp ./cyoda_mcp
COPY application ./application
COPY common ./common
COPY services ./services

# Install the package in editable mode (same as local development)
RUN pip install -e .

# Create non-root user
RUN useradd -m -s /bin/bash appuser && \
    echo "appuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set ownership and permissions efficiently
RUN chown -R appuser:appuser /app && \
    find /app -name "*.sh" -exec chmod +x {} \;

# Verify installations
RUN python --version && \
    pip --version && \
    pipx --version && \
    poetry --version && \
    java --version && \
    gradle --version && \
    mvn --version && \
    node --version && \
    npm --version && \
    ps --version && \
    echo "Testing ps command functionality:" && \
    ps -eo pid,ppid,user,stat,etime,cmd --no-headers | head -5 && \
    echo "Verifying Unix commands for GitHub tools:" && \
    find --version | head -1 && \
    grep --version | head -1 && \
    ls --version | head -1 && \
    cat --version | head -1 && \
    head --version | head -1 && \
    tail --version | head -1 && \
    file --version && \
    sort --version | head -1 && \
    uniq --version | head -1 && \
    cut --version | head -1 && \
    awk --version | head -1 && \
    sed --version | head -1 && \
    tr --version | head -1 && \
    wc --version | head -1 && \
    nl --version | head -1 && \
    basename --version | head -1 && \
    dirname --version | head -1 && \
    realpath --version | head -1 && \
    readlink --version | head -1 && \
    tar --version | head -1 && \
    gzip --version | head -1 && \
    gunzip --version | head -1 && \
    zcat --version | head -1 && \
    jq --version && \
    tree --version && \
    du --version | head -1 && \
    stat --version | head -1 && \
    less --version | head -1 && \
    echo "✅ All required Unix commands are available!"

# Configure Git (GitHub App authentication is used instead of personal tokens)
RUN git config --global user.email "app-builder@example.com" && \
    git config --global user.name "app-builder"

# Switch to non-root user
USER appuser

# Set up Python environment for appuser
ENV PATH="/home/appuser/.local/bin:$PATH"
RUN pipx ensurepath

# Configure Git for appuser (GitHub App authentication is used for repository access)
RUN git config --global user.email "app-builder@example.com" && \
    git config --global user.name "app-builder"

# Expose port
EXPOSE 5000

# Run the application with extended timeout for long-running tool executions
# --keep-alive-timeout: 600 seconds (10 minutes) for SSE streaming
# --graceful-timeout: 30 seconds for graceful shutdown
CMD ["hypercorn", "application.app:app", "--bind", "0.0.0.0:5000", "--keep-alive", "600", "--graceful-timeout", "30"]