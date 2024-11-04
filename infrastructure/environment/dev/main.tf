provider "aws" {
  region = "eu-west-2"
  access_key = var.AWS_ACCESS_KEY
  secret_key = var.AWS_SECRET_KEY
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.17.0"
    }
  }
}

module "network" {
  source        = "../../modules/network"
  naming_prefix = local.naming_prefix
}

module "sg" {
  source        = "../../modules/sg"
  naming_prefix = local.naming_prefix
  vpc_id        = module.network.vpc_id
}

module "ec2" {
  source        = "../../modules/ec2"
  naming_prefix = local.naming_prefix
  ec2_sg_id     = [module.sg.ec2_sg_id]
  subnet_id     = module.network.subnet_id
}