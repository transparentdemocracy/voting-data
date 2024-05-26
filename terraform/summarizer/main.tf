provider "aws" {
  region = "eu-west-1"
}

resource "aws_instance" "summarizer" {
  ami           = "ami-0ac67a26390dc374d"
  instance_type = "t2.micro"
  key_name      = "${var.ec2_keypair_name}"
  iam_instance_profile = aws_iam_instance_profile.summarizer.name

  network_interface {
    network_interface_id = aws_network_interface.summarizer.id
    device_index         = 0
  }

  tags = {
    Name = "td-summarizer"
  }
}

resource "aws_network_interface" "summarizer" {
  subnet_id   = var.subnet_id
}

resource "aws_iam_instance_profile" "summarizer" {
  name = "summarizer"
  role = aws_iam_role.summarizer.name
}

resource "aws_iam_role" "summarizer" {
  name = "summarizer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "summarizer" {
  name = "summarizer-policy"
  role = aws_iam_role.summarizer.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = [
        "s3:*"
      ],
      Effect = "Allow",
      Resource = "*"
    }]
  })
}
