terraform {
    required_providers {
      adguard = {
        source = "gmichels/adguard"
        version = "1.5.0"
      }
    }
}

# configuration for the provider
provider "adguard" {
  host     = "localhost:8080"
  username = "admin"
  password = var.ADGUARD_PASSWORD
  scheme   = "https" # defaults to https
  timeout  = 5      # in seconds, defaults to 10
  insecure = false  # when `true` will skip TLS validation
}
variable "ADGUARD_PASSWORD" {
    type = string
    sensitive = true
 }