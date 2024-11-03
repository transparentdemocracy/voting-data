
output "function_arn" {
  description = "ARN of the Lambda function"
  value = {
    for v in local.functions: v.key => aws_lambda_function.function[v.key].arn
  }
}

output "function_invoke_arn" {
  description = "ARN of the Lambda function"
  value = {
    for v in local.functions: v.key => aws_lambda_function.function[v.key].invoke_arn
  }
}

output "function_url" {
  description = "URL of the Lambda function"
  value = {
    for v in local.functions: v.key => aws_lambda_function_url.function_url[v.key].function_url
  }
}
