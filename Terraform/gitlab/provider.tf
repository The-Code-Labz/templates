terraform {
    required_providers {
      gitlab = {
        source = "gitlabhq/gitlab"
        version = "17.9.0"
      }
    }
}
  
  provider "gitlab" {
    # Configuration options
    base_url = "https://gitlab.neurolearninglabs.com/api/v4"
    token = var.GITLAB_TOKEN
}
variable "GITLAB_TOKEN" {
    type = string 
    sensitive = true
}