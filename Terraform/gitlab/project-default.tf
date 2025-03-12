resource "gitlab_project" "your-project" {
    name        = "your-project"
    description = ""
  
    visibility_level = "internal"
  
    wiki_enabled = false
    packages_enabled = false
    auto_devops_enabled = false
    initialize_with_readme = true
  #  avatar = "/path/to/image"
  #  avatar_hash = filesha256("/path/to/image")
}
  resource "gitlab_project_hook" "your-project" {
    project = project_id
    url = var.RENOVATE_WEBHOOK_URL
    token = var.RENOVATE_WEBHOOK_SECRET
    push_events = false
    issues_events = true
    enable_ssl_verification = true
}
resource "gitlab_project_membership" "your-project" {
    project      = "project_id"
    user_id      = user_id
    access_level = "maintainer"
}