# syntax=docker/dockerfile:1
FROM debian:12

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential tools for LPIC-1 practice
# Covers: file management, users, permissions, networking, systemd, packages, shells, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core utilities (LPIC-1 Objective 100-101: Linux Installation & Hardware)
    curl \
    wget \
    gpg \
    # Shell & text processing (LPIC-1 Objective 100-103: Shells)
    bash \
    vim \
    less \
    tree \
    jq \
    # File & disk management (LPIC-1 Objective 100-104: FS & Disk Management)
    e2fsprogs \
    fdisk \
    lvm2 \
    util-linux \
    # Users & groups (LPIC-1 Objective 100-105: Users & Groups)
    sudo \
    # Networking (LPIC-1 Objective 100-107: Networking)
    iproute2 \
    iputils-ping \
    net-tools \
    dnsutils \
    nmap \
    # System administration (LPIC-1 Objective 100-108: System Startup & Boot)
    systemd \
    # Package management (LPIC-1 Objective 100-106: Applications)
    apt-transport-https \
    software-properties-common \
    # Development tools (LPIC-1 Objective 100-109: Dev Basics)
    build-essential \
    git \
    # Monitoring & logging (LPIC-1 Objective 100-110: Security)
    procps \
    sysstat \
    htop \
    strace \
    ltrace \
    # Compression & archives
    tar \
    gzip \
    bzip2 \
    xz-utils \
    zip \
    unzip \
    # Cron & scheduling
    cron \
    # SSH server for practice
    openssh-server \
    # Text & character encoding
    locales \
    # Man pages
    man-db \
    manpages \
    manpages-dev \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Generate locale for en_US.UTF-8
RUN sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Create a non-root user "student" for practice (LPIC-1 user management)
ARG USERNAME=student
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid "$USER_GID" "$USERNAME" && \
    useradd --uid "$USER_UID" --gid "$USER_GID" -m -s /bin/bash "$USERNAME" && \
    echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/"$USERNAME" && \
    chmod 0440 "/etc/sudoers.d/$USERNAME"

# Clone dotfiles to a temporary location for the entrypoint to copy
ARG DOTFILES_REPO=https://github.com/lpoblet/dotfiles
RUN git clone "$DOTFILES_REPO" /opt/dotfiles

# Copy entrypoint script that initializes the home directory on first run
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set working directory
WORKDIR "/home/$USERNAME"

# Switch to the student user
USER "$USERNAME"

# Use entrypoint to initialize, then drop to shell
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
