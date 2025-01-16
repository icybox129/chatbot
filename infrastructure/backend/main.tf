# terraform {
#     backend "s3" {
#         bucket = ""
#         key = ""
#         region = "eu-west-2"
#         encrypt = true
#     }
# }

provider "aws" {
  region = "eu-west-2"
}

resource "aws_s3_bucket" "terraform_state" {
  bucket_prefix = "terraform-state-"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}


output "bucket_name" {
  value = aws_s3_bucket.terraform_state.bucket
}

output "bucket_id" {
  value = aws_s3_bucket.terraform_state.id
}

output "bucket_arn" {
  value = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.terraform_state_lock.name
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.terraform_state_lock.arn
}