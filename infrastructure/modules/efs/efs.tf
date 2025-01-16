resource "aws_efs_file_system" "chroma_efs" {
  creation_token   = "chroma-efs"
  performance_mode = "generalPurpose"
  encrypted        = true

  tags = {
    Name = "${var.naming_prefix}-chroma-efs"
  }
}

resource "aws_efs_mount_target" "chroma_mnt" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.chroma_efs.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [var.efs_sg]
}