provider "aws" {
  region = "eu-west-2"
  # access_key = var.AWS_ACCESS_KEY
  # secret_key = var.AWS_SECRET_KEY
}

terraform {
  backend "s3" {
    bucket = "nick-test-state-20250108152540296300000001"
    key = "dev/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.17.0"
    }
  }
}

module "alb" {
  source            = "../../modules/alb"
  naming_prefix     = local.naming_prefix
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  alb_sg_id         = module.sg.alb_sg_id
}

module "cloudwatch" {
  source        = "../../modules/cloudwatch"
  naming_prefix = local.naming_prefix
}

# module "ec2" {
#   source        = "../../modules/ec2"
#   naming_prefix = local.naming_prefix
#   ec2_sg_id     = [module.sg.ec2_sg_id]
#   subnet_id     = module.network.subnet_id
# }

module "ecr" {
  source        = "../../modules/ecr"
  naming_prefix = local.naming_prefix
}

module "ecs" {
  source                 = "../../modules/ecs"
  naming_prefix          = local.naming_prefix
  ecs_container_instance = [module.sg.ecs_container_instance]
  private_subnet_ids     = module.network.private_subnet_ids
  log_group_name         = module.cloudwatch.log_group_name
  alb_target_group_arn   = module.alb.alb_target_group_arn
  openai_api_key_arn     = module.secrets_manager.openai_api_key_arn
  ecr_repository_url     = module.ecr.ecr_repository_url
}

module "network" {
  source        = "../../modules/network"
  naming_prefix = local.naming_prefix
}

module "secrets_manager" {
  source         = "../../modules/secrets_manager"
  naming_prefix  = local.naming_prefix
  openai_api_key = var.openai_api_key
}

module "sg" {
  source        = "../../modules/sg"
  naming_prefix = local.naming_prefix
  vpc_id        = module.network.vpc_id
}