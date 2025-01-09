output "ecr_repository_url" {
  value = module.ecr.aws_ecr_repository.ecr.repository_url
}
