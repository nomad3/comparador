variable "gcp_project_id" {
  description = "The GCP project ID to deploy resources into."
  type        = string
  # default     = "your-gcp-project-id" # Or set via TF_VAR_gcp_project_id env var / terraform.tfvars
}

variable "gcp_region" {
  description = "The GCP region to deploy resources into."
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "The GCP zone within the region to deploy the VM."
  type        = string
  default     = "us-central1-a"
}

variable "vm_name" {
  description = "Name for the Google Compute Engine instance."
  type        = string
  default     = "comparador-precios-vm"
}

variable "vm_machine_type" {
  description = "The machine type for the GCE instance."
  type        = string
  default     = "e2-medium" # Cost-effective option, adjust as needed
}

variable "vm_image" {
  description = "The boot disk image for the GCE instance (e.g., Debian or Ubuntu)."
  type        = string
  default     = "debian-cloud/debian-11" # Debian 11 is common and stable
  # Alternative: "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "vm_disk_size_gb" {
  description = "The size of the boot disk in GB."
  type        = number
  default     = 20 # Adjust based on expected usage
}

variable "vm_tags" {
  description = "Network tags to apply to the VM instance for firewall rules."
  type        = list(string)
  default     = ["http-server", "https-server", "ssh"] # Tags for common ports
}

variable "ssh_user" {
  description = "The default user for SSH access (often depends on the image)."
  type        = string
  default     = "devops" # Example user, adjust as needed
}

variable "ssh_public_key" {
  description = "The SSH public key content to allow access to the VM."
  type        = string
  sensitive   = true # Mark as sensitive, don't log the key
  # default   = "ssh-rsa AAAAB3NzaC1yc2EAAA..." # Set via TF_VAR_ssh_public_key or terraform.tfvars
}
