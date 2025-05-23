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

variable "wddp_firebase_service_account_base64" {
    description = "firebase service account info"
    type        = string
}

variable "cors_allow_origins" {
    description = "CORS allow origins"
    type = list(string)
    default = [ "*" ]
}
