variable "environment" {
  description = "environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "wddp_prod_es_auth" {
  description = "Elasticsearch credentials"
  type        = string
}

variable "cors_allow_origins" {
  description = "CORS allow origins"
  type        = list(string)
}

variable "wddp_firebase_service_account_base64" {
  description = "Firebase service account info"
  type        = string
}


