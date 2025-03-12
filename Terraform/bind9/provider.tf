terraform {
    required_providers {
      dns = {
        source = "hashicorp/dns"
        version = "3.4.2"
      }
    }
}
  
  provider "dns" {
    update {
      server        = "192.168.0.1"
      key_name      = "example.com."
      key_algorithm = "hmac-md5"
      key_secret    = "3VwZXJzZWNyZXQ="
    }
}

