# manage a DNS rewrite rule
resource "adguard_rewrite" "test" {
  domain = "example.com"
  answer = "4.3.2.1"
}

# get a DNS rewrite rule
data "adguard_rewrite" "test" {
  domain = "example.org"
}