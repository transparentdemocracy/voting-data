resource "aws_security_group" "summarizer" {
  name        = "summarizer"
  description = "Allow SSH and HTTP access"
  vpc_id      = var.vpc_id  # Replace with your VPC ID

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "summarizer"
  }
}


