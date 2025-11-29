# Terraform Configuration for AWS S3 Bucket
# Specifications implemented:
# - Bucket name: "my-example-app-bucket-12345" 
# - Enable versioning
# - Enable server-side encryption with AWS KMS
# - Block all public access
# - Add lifecycle rules to transition objects to different storage classes
# - Enable CloudWatch metrics for monitoring
# - Configure lifecycle rule to delete incomplete multipart uploads after 7 days
# - Set up appropriate IAM policies for secure access
# - Add tags: Environment="dev", Project="example-app", Owner="devops-team"

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region where S3 bucket will be created"
  type        = string
  default     = "us-west-2"
}

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
  default     = "my-example-app-bucket-12345"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project tag"
  type        = string
  default     = "example-app"
}

variable "owner" {
  description = "Owner tag"
  type        = string
  default     = "devops-team"
}

# Create S3 Bucket
resource "aws_s3_bucket" "app_bucket" {
  bucket = var.bucket_name
  
  tags = {
    Environment = var.environment
    Project     = var.project
    Owner       = var.owner
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "app_bucket_versioning" {
  bucket = aws_s3_bucket.app_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "app_bucket_encryption" {
  bucket = aws_s3_bucket.app_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_kms_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# Create KMS key for S3 encryption
resource "aws_kms_key" "s3_kms_key" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 7
  
  tags = {
    Environment = var.environment
    Project     = var.project
    Owner       = var.owner
  }
}

resource "aws_kms_alias" "s3_kms_alias" {
  name          = "alias/${var.bucket_name}-encryption"
  target_key_id = aws_kms_key.s3_kms_key.key_id
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "app_bucket_public_access" {
  bucket                  = aws_s3_bucket.app_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable CloudWatch metrics
resource "aws_s3_bucket_metric" "app_bucket_metrics" {
  bucket = aws_s3_bucket.app_bucket.id
  name   = "EntireBucket"
}

# Lifecycle rules for storage class transitions
resource "aws_s3_bucket_lifecycle_configuration" "app_bucket_lifecycle" {
  bucket = aws_s3_bucket.app_bucket.id
  
  rule {
    id     = "storage_class_transitions"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
  
  rule {
    id     = "incomplete_multipart_cleanup"
    status = "Enabled"
    
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# IAM Policy for secure access
resource "aws_iam_policy" "s3_bucket_policy" {
  name        = "${var.bucket_name}-policy"
  description = "IAM policy for secure S3 bucket access"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.app_bucket.arn,
          "${aws_s3_bucket.app_bucket.arn}/*"
        ]
        Principal = {
          AWS = var.allowed_iam_principals
        }
        Condition = {
          Bool = {
            "aws:SecureTransport" = "true"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.s3_kms_key.arn
        Principal = {
          AWS = var.allowed_iam_principals
        }
      }
    ]
  })
}

variable "allowed_iam_principals" {
  description = "List of IAM principals allowed to access the S3 bucket"
  type        = list(string)
  default     = ["arn:aws:iam::123456789012:user/developer"]
}

# Outputs
output "bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.app_bucket.bucket
}

output "bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.app_bucket.arn
}

output "kms_key_arn" {
  description = "ARN of the KMS encryption key"
  value       = aws_kms_key.s3_kms_key.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the bucket"
  value       = aws_s3_bucket.app_bucket.bucket_regional_domain_name
}
