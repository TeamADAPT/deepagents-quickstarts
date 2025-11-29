# Production-Ready AWS S3 Bucket Terraform Configuration
# Features: Versioning, KMS encryption, Lifecycle policies, Object lock, CORS, Replication, Event notifications

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider Configuration
provider "aws" {
  region = var.primary_region
  alias  = "primary"
}

provider "aws" {
  region = var.replica_region
  alias  = "replica"
}

# Variables
variable "primary_region" {
  description = "Primary region for S3 bucket"
  type        = string
  default     = "us-west-2"
}

variable "replica_region" {
  description = "Replica region for cross-region replication"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Name of the production S3 bucket"
  type        = string
  default     = "production-app-data-bucket-2024"
}

variable "replica_bucket_name" {
  description = "Name of the replica S3 bucket for DR"
  type        = string
  default     = "production-app-data-bucket-2024-replica"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "production"
}

variable "application" {
  description = "Application tag"
  type        = string
  default     = "web-app"
}

variable "team" {
  description = "Team tag"
  type        = string
  default     = "platform-engineering"
}

variable "cost_center" {
  description = "Cost center tag"
  type        = string
  default     = "cc-12345"
}

variable "object_lock_retention_days" {
  description = "Object lock retention period in days"
  type        = number
  default     = 2555  # 7 years for compliance
}

variable "notification_lambda_function_arn" {
  description = "ARN of Lambda function for S3 event notifications"
  type        = string
  default     = "arn:aws:lambda:us-west-2:123456789012:function:s3-notification-handler"
}

variable "allowed_notification_events" {
  description = "S3 events that trigger notifications"
  type        = list(string)
  default     = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*", "s3:ObjectRestore:*"]
}

# Common tags
locals {
  common_tags = {
    Environment   = var.environment
    Application   = var.application
    Team          = var.team
    CostCenter    = var.cost_center
    ManagedBy     = "Terraform"
    CreatedDate   = timestamp()
  }
}

# KMS Customer Managed Key for encryption
resource "aws_kms_key" "s3_encryption_key" {
  description             = "KMS key for production S3 bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = local.common_tags
}

resource "aws_kms_alias" "s3_encryption_alias" {
  name          = "alias/${var.bucket_name}-encryption"
  target_key_id = aws_kms_key.s3_encryption_key.key_id
}

# Primary S3 Bucket
resource "aws_s3_bucket" "primary_bucket" {
  bucket = var.bucket_name
  
  tags = local.common_tags
}

# Replica S3 Bucket for cross-region replication
resource "aws_s3_bucket" "replica_bucket" {
  provider = aws.replica
  bucket   = var.replica_bucket_name
  
  tags = local.common_tags
}

# Enable versioning on primary bucket
resource "aws_s3_bucket_versioning" "primary_versioning" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning on replica bucket
resource "aws_s3_bucket_versioning" "replica_versioning" {
  provider = aws.replica
  bucket   = aws_s3_bucket.replica_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption with KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "primary_encryption" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_encryption_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "replica_encryption" {
  provider = aws.replica
  bucket   = aws_s3_bucket.replica_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Object Lock Configuration for compliance
resource "aws_s3_bucket_object_lock_configuration" "primary_object_lock" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.object_lock_retention_days
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "replica_object_lock" {
  provider = aws.replica
  bucket   = aws_s3_bucket.replica_bucket.id
  
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.object_lock_retention_days
    }
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "primary_public_access" {
  bucket                  = aws_s3_bucket.primary_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "replica_public_access" {
  provider = aws.replica
  bucket   = aws_s3_bucket.replica_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS Configuration for web application
resource "aws_s3_bucket_cors_configuration" "web_app_cors" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  cors_rule {
    allowed_methods = ["GET", "POST", "PUT", "HEAD"]
    allowed_origins = ["https://*.example.com", "https://app.example.com"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "x-amz-meta-custom-header"]
    max_age_seconds = 3000
  }
}

# Lifecycle Configuration with storage class transitions
resource "aws_s3_bucket_lifecycle_configuration" "primary_lifecycle" {
  bucket = aws_s3_bucket.primary_bucket.id
  
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
      days_after_initiation = 3
    }
  }
  
  rule {
    id     = "expired_object_delete"
    status = "Enabled"
    
    expiration {
      days = 2555  # 7 years
    }
  }
}

# CloudWatch Storage Metrics
resource "aws_s3_bucket_metric" "primary_storage_metrics" {
  bucket = aws_s3_bucket.primary_bucket.id
  name   = "EntireBucket"
}

# Event Notifications
resource "aws_s3_bucket_notification" "primary_notifications" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  lambda_function {
    lambda_function_arn = var.notification_lambda_function_arn
    events              = var.allowed_notification_events
    filter_prefix       = "uploads/"
  }
}

# Cross-Region Replication Configuration
resource "aws_s3_bucket_replication_configuration" "primary_replication" {
  role   = aws_iam_role.replication_role.arn
  bucket = aws_s3_bucket.primary_bucket.id
  
  rule {
    id     = "replication-rule"
    status = "Enabled"
    
    destination {
      bucket        = aws_s3_bucket.replica_bucket.arn
      storage_class = "STANDARD_IA"
      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }
  }
}

# IAM Role for replication
resource "aws_iam_role" "replication_role" {
  name = "${var.bucket_name}-replication-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM Policy for replication
resource "aws_iam_policy" "replication_policy" {
  name = "${var.bucket_name}-replication-policy"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = [
          "${aws_s3_bucket.primary_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.primary_bucket.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = [
          "${aws_s3_bucket.replica_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "replication_policy_attachment" {
  role       = aws_iam_role.replication_role.name
  policy_arn = aws_iam_policy.replication_policy.arn
}

# Bucket Policy for additional security
resource "aws_s3_bucket_policy" "primary_bucket_policy" {
  bucket = aws_s3_bucket.primary_bucket.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.primary_bucket.arn,
          "${aws_s3_bucket.primary_bucket.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
          StringNotEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_id
          }
        }
      }
    ]
  })
}

variable "vpc_endpoint_id" {
  description = "VPC Endpoint ID for private access"
  type        = string
  default     = "vpce-12345"
}

# Outputs
output "primary_bucket_name" {
  description = "Name of the primary S3 bucket"
  value       = aws_s3_bucket.primary_bucket.bucket
}

output "primary_bucket_arn" {
  description = "ARN of the primary S3 bucket"
  value       = aws_s3_bucket.primary_bucket.arn
}

output "replica_bucket_name" {
  description = "Name of the replica S3 bucket"
  value       = aws_s3_bucket.replica_bucket.bucket
}

output "replica_bucket_arn" {
  description = "ARN of the replica S3 bucket"
  value       = aws_s3_bucket.replica_bucket.arn
}

output "kms_key_arn" {
  description = "ARN of the KMS encryption key"
  value       = aws_kms_key.s3_encryption_key.arn
}

output "replication_role_arn" {
  description = "ARN of the replication IAM role"
  value       = aws_iam_role.replication_role.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the primary bucket"
  value       = aws_s3_bucket.primary_bucket.bucket_regional_domain_name
}
