output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "vpc_cidr_block" {
  value = var.vpc_cidr_block
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}