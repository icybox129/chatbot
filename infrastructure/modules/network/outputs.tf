output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "subnet_id" {
  value = aws_subnet.public.id
}

output "vpc_cidr_block" {
  value = var.vpc_cidr_block
}