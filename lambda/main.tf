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

# Create ZIP file for Lambda function
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/lambda_function.zip"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

# Lambda function
resource "aws_lambda_function" "function" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.function_name
  role            = aws_iam_role.lambda_role.arn
  handler         = "search_motions.search_motions"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.9"
  layers = [aws_lambda_layer_version.requests_layer.arn]

  environment {
    variables = {
      ES_AUTH = var.es_auth
    }
  }
}

# Create a temporary directory for pip installations
#resource "null_resource" "pip_install" {
#  triggers = {
#    requirements_md5 = filemd5("${path.module}/requirements.txt")
#  }
#
#  provisioner "local-exec" {
#    command = <<EOF
#      rm -rf ${path.module}/python
#      mkdir -p ${path.module}/python/lib/python3.9/site-packages
#      pip install -r ${path.module}/requirements.txt -t ${path.module}/python/lib/python3.9/site-packages/
#    EOF
#  }
#}

# Create ZIP file for Lambda Layer
data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/package"
  output_path = "${path.module}/lambda_layer.zip"
  
  #depends_on = [null_resource.pip_install]
}

# Create Lambda Layer
resource "aws_lambda_layer_version" "requests_layer" {
  filename            = data.archive_file.lambda_layer.output_path
  layer_name         = "requests-layer"
  description        = "Python Requests Library"
  compatible_runtimes = ["python3.9"]
  
  depends_on = [data.archive_file.lambda_layer]
}

