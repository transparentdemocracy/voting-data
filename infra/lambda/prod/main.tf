terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.73"
    }
  }
  backend "s3" {
    bucket         = "wddp-terraform-prod"
    key            = "lambdas/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

module "wddp_lambdas" {
    source = "../modules/wddp_lambdas"

    environment = var.environment
    es_auth = var.wddp_prod_es_auth
}
