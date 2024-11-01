variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "search_motions"
}

variable "es_auth" {
  description = "Elasticsearch auth"
  type        = string
}
