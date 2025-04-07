terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Use a recent version
    }
  }
  required_version = ">= 1.0" # Specify minimum Terraform version
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# --- Networking ---

# Use the default VPC network for simplicity in MVP
data "google_compute_network" "default" {
  name = "default"
}

# Firewall rule to allow HTTP traffic (Port 80)
resource "google_compute_firewall" "allow_http" {
  name    = "${var.vm_name}-allow-http"
  network = data.google_compute_network.default.name
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
  target_tags   = ["http-server"] # Apply to VMs with this tag
  source_ranges = ["0.0.0.0/0"]   # Allow traffic from any IP (adjust if needed)
  description   = "Allow HTTP traffic for web server"
}

# Firewall rule to allow HTTPS traffic (Port 443) - Optional for MVP if not using SSL yet
resource "google_compute_firewall" "allow_https" {
  name    = "${var.vm_name}-allow-https"
  network = data.google_compute_network.default.name
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
  target_tags   = ["https-server"] # Apply to VMs with this tag
  source_ranges = ["0.0.0.0/0"]    # Allow traffic from any IP (adjust if needed)
  description   = "Allow HTTPS traffic for web server"
}

# Firewall rule to allow SSH traffic (Port 22)
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.vm_name}-allow-ssh"
  network = data.google_compute_network.default.name
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  target_tags   = ["ssh"] # Apply to VMs with this tag
  # IMPORTANT: Restrict source_ranges for SSH to known IPs for security
  # Example: source_ranges = ["YOUR_HOME_OR_OFFICE_IP/32"]
  source_ranges = ["0.0.0.0/0"] # WARNING: Allows SSH from anywhere, replace in production
  description   = "Allow SSH access"
}


# --- Compute Engine Instance ---

resource "google_compute_instance" "vm_instance" {
  name         = var.vm_name
  machine_type = var.vm_machine_type
  zone         = var.gcp_zone
  tags         = var.vm_tags # Apply tags for firewall rules

  boot_disk {
    initialize_params {
      image = var.vm_image
      size  = var.vm_disk_size_gb
    }
  }

  # Define the network interface using the default network
  network_interface {
    network = data.google_compute_network.default.name
    # Access config needed to assign an external IP address
    access_config {
      // Ephemeral external IP will be assigned
    }
  }

  # Metadata for startup script and SSH keys
  metadata = {
    # Add SSH key for the specified user
    ssh-keys = "${var.ssh_user}:${var.ssh_public_key}"

    # Startup script to install Docker and Docker Compose
    # Reference the script file (more maintainable)
    startup-script = file("${path.module}/../scripts/startup-script.sh")
    # Alternative: Inline script (less maintainable)
    # startup-script = <<-EOF
    #   #!/bin/bash
    #   echo "Starting startup script..."
    #   # Update package list
    #   apt-get update -y
    #   # Install prerequisites
    #   apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git
    #   # Add Docker's official GPG key
    #   mkdir -p /etc/apt/keyrings
    #   curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    #   # Set up the stable repository
    #   echo \
    #     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    #     $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    #   # Install Docker Engine
    #   apt-get update -y
    #   apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    #   # Add default user to docker group (adjust 'devops' if needed)
    #   usermod -aG docker devops || echo "User devops might not exist yet"
    #   echo "Docker and Docker Compose installed."
    #   # Optional: Install other tools like git, etc.
    #   echo "Startup script finished."
    # EOF
  }

  # Allow the instance to be deleted when running `terraform destroy`
  allow_stopping_for_update = true

  # Service account - use default compute engine service account for simplicity
  # For production, consider a dedicated service account with least privilege
  service_account {
    # email  = "..." # Specify custom service account email if needed
    scopes = [
      "https://www.googleapis.com/auth/cloud-platform", # Broad scope, refine if needed
      # "https://www.googleapis.com/auth/logging.write",
      # "https://www.googleapis.com/auth/monitoring.write",
      # "https://www.googleapis.com/auth/devstorage.read_only",
    ]
  }

  # Optional: Add labels for organization
  labels = {
    environment = "development" # Or "production"
    app         = "comparador-precios"
  }
}
