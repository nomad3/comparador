#!/bin/bash
# This script is executed by GCE instance metadata `startup-script`
# It installs Docker and Docker Compose plugin.

set -e # Exit immediately if a command exits with a non-zero status.
set -x # Print commands and their arguments as they are executed.

echo "Starting startup script execution..."
export DEBIAN_FRONTEND=noninteractive # Prevent interactive prompts

# --- Update System ---
echo "Updating package list..."
apt-get update -y

echo "Upgrading existing packages..."
# Use dist-upgrade to handle changing dependencies, new kernels, etc.
apt-get dist-upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# --- Install Prerequisites ---
echo "Installing prerequisites (curl, gnupg, lsb-release, git)..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    software-properties-common # Often needed

# --- Install Docker ---
echo "Installing Docker..."
# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the Docker repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package list again after adding Docker repo
apt-get update -y

# Install Docker Engine, CLI, Containerd, and Compose plugin
echo "Installing Docker packages..."
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify Docker installation
docker --version
docker compose version

# --- Add User to Docker Group ---
# This allows running docker commands without sudo
# Replace 'devops' with the actual username defined in Terraform variable 'ssh_user' if different
SSH_USER="devops" # Default, consider passing this in if variable
if id -u "$SSH_USER" >/dev/null 2>&1; then
    echo "Adding user '$SSH_USER' to the docker group..."
    usermod -aG docker "$SSH_USER"
    echo "User '$SSH_USER' added to docker group. Changes will apply on next login."
else
    echo "Warning: User '$SSH_USER' not found. Cannot add to docker group."
fi

# --- Cleanup ---
echo "Cleaning up apt cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Startup script finished successfully."

# Optional: Reboot the instance for group changes to take full effect for the user
# echo "Rebooting instance..."
# reboot
