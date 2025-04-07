output "vm_instance_name" {
  description = "The name of the created GCE instance."
  value       = google_compute_instance.vm_instance.name
}

output "vm_instance_external_ip" {
  description = "The external IP address of the GCE instance."
  value       = google_compute_instance.vm_instance.network_interface[0].access_config[0].nat_ip
}

output "vm_instance_internal_ip" {
  description = "The internal IP address of the GCE instance."
  value       = google_compute_instance.vm_instance.network_interface[0].network_ip
}

output "ssh_command" {
  description = "Command to SSH into the VM instance."
  value       = "ssh ${var.ssh_user}@${google_compute_instance.vm_instance.network_interface[0].access_config[0].nat_ip}"
  # Note: Assumes your private key corresponding to var.ssh_public_key is configured locally.
}
