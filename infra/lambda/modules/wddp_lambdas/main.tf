terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 5.73"
        }
    }
}

locals {
    functions = [
        { key : "get_motion", name : "get-motion-${var.environment}", handler : "wddp.get_motion" },
        { key : "search_motions", name : "search-motions-${var.environment}", handler : "wddp.search_motions" },
        { key : "search_plenaries", name : "search-plenaries-${var.environment}", handler : "wddp.search_plenaries" },
    ]
}

provider "aws" {
    region = var.aws_region
}

data "archive_file" "lambda_zip" {
    type        = "zip"
    source_dir  = "${path.module}/wddp"
    output_path = "${path.module}/lambda_function.zip"
}

resource "aws_iam_role" "lambda_role" {
    name = "wddp-lambdas-${var.environment}-role"

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

resource "aws_iam_role_policy_attachment" "lambda_basic" {
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    role       = aws_iam_role.lambda_role.name
}

resource "aws_lambda_function" "function" {
    for_each = {for func in local.functions : func.key => func}

    filename         = data.archive_file.lambda_zip.output_path
    function_name    = each.value.name
    role             = aws_iam_role.lambda_role.arn
    handler          = each.value.handler
    source_code_hash = data.archive_file.lambda_zip.output_base64sha256
    runtime          = "python3.11"
    layers = [aws_lambda_layer_version.requests_layer.arn]

    environment {
        variables = {
            ES_AUTH = var.es_auth
            FIREBASE_SERVICE_ACCOUNT_INFO = base64decode(var.wddp_firebase_service_account_base64)
        }
    }
}

resource "aws_lambda_function_url" "function_url" {
    for_each           = {for func in local.functions : func.key => func}
    function_name      = aws_lambda_function.function[each.key].function_name
    authorization_type = "NONE"
    cors {
        allow_credentials = true
        allow_origins     = var.cors_allow_origins
        allow_methods = ["GET"]
        allow_headers = ["date", "keep-alive", "authorization"]
        expose_headers = ["keep-alive", "date"]
        max_age           = 3600
    }
}

resource "aws_lambda_permission" "url" {
    for_each               = {for func in local.functions : func.key => func}
    statement_id           = "FunctionURLAllowPublicAccess"
    action                 = "lambda:InvokeFunctionUrl"
    function_name          = aws_lambda_function.function[each.key].function_name
    principal              = "*"
    function_url_auth_type = "NONE"
}

resource "null_resource" "pip_install" {
    triggers = {
        requirements_md5 = filemd5("${path.module}/requirements.txt")
    }

    provisioner "local-exec" {
        command = <<EOF
      rm -rf ${path.module}/package/python
      mkdir -p ${path.module}/package/python/lib/python3.11/site-packages
      pip3.11 install -r ${path.module}/requirements.txt -t ${path.module}/package/python/lib/python3.11/site-packages/
    EOF
    }
}

data "archive_file" "lambda_layer" {
    type        = "zip"
    source_dir  = "${path.module}/package"
    output_path = "${path.module}/lambda_layer.zip"

    depends_on = [null_resource.pip_install]
}

resource "aws_lambda_layer_version" "requests_layer" {
    filename    = data.archive_file.lambda_layer.output_path
    source_code_hash = filebase64sha256(data.archive_file.lambda_layer.output_path)
    layer_name  = "requests-layer-${var.environment}"
    description = "Python Requests Library"
    compatible_runtimes = ["python3.11"]

    depends_on = [data.archive_file.lambda_layer]
}
