variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "environment"
  type        = string
}

variable "es_auth" {
  description = "Elasticsearch auth"
  type        = string
}
