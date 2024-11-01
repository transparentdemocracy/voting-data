
output "function_arn" {
  description = "ARN of the Lambda function"
  value = {
    for v in local.functions: v.name => aws_lambda_function.function[v.name].arn
  }
}

output "function_invoke_arn" {
  description = "ARN of the Lambda function"
  value = {
    for v in local.functions: v.name => aws_lambda_function.function[v.name].invoke_arn
  }
}

output "function_url" {
  description = "URL of the Lambda function"
  value = {
    for v in local.functions: v.name => aws_lambda_function_url.function_url[v.name].function_url
  }
}
