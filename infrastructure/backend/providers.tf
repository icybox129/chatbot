# terraform {
#   backend "s3" {
#     bucket = "nick-test-state-20250108152540296300000001"
#     key = "backend/terraform.tfstate"
#     region = "us-east-1"
#     encrypt = true
#   }
# }

resource "aws_s3_bucket" "s3bucket" {
    bucket_prefix = "nick-test-state-"
    force_destroy = true
}

output "bucket-name" {
    value = aws_s3_bucket.s3bucket.bucket
}