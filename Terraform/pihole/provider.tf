terraform {
    required_providers {
      pihole = {
        source = "ryanwholey/pihole"
        version = "0.2.0"
      }
    }
}
  
provider "pihole" {
    url = "https://pihole.domain.com" # PIHOLE_URL
    api_token = var.pihole_api_token # PIHOLE_API_TOKEN  or password = var.pihole_password   
}