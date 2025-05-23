terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.73"
    }
  }
  backend "s3" {
    bucket         = "wddp-terraform-dev"
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
    es_auth = var.wddp_dev_es_auth
    wddp_firebase_service_account_base64 = var.wddp_firebase_service_account_base64
    cors_allow_origins = var.cors_allow_origins
}
