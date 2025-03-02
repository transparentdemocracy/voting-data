variable "environment" {
  description = "environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "wddp_dev_es_auth" {
  description = "Elasticsearch credentials"
  type        = string
}

