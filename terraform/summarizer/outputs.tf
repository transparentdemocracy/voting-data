
output "public_ip" {
  description = "The public IP address of the summarizer EC2 instance"
  value       = aws_instance.summarizer.public_ip
}

