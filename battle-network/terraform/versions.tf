terraform {
  required_version = ">= 1.7, < 2.0"
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = ">= 3.0, < 4.0"
    }
  }
}

# Credentials stay in existing OS_* environment variables or clouds.yaml.
provider "openstack" {
  cloud = var.cloud_name
}
