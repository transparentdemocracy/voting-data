terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.73"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "wddp_lambdas" {
    source = "../modules/wddp_lambdas"

    environment = var.environment
    es_auth = var.wddp_dev_es_auth
}
