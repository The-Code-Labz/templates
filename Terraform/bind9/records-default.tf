resource "dns_a_record_set" "www" {
    zone = "example.com."
    name = "www"
    addresses = [
      "192.168.0.1",
      "192.168.0.2",
      "192.168.0.3",
    ]
    ttl = 300
}

resource "dns_ns_record_set" "www" {
    zone = "example.com."
    name = "www"
    nameservers = [
      "a.iana-servers.net.",
      "b.iana-servers.net.",
    ]
    ttl = 300
}