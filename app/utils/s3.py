"""
AWS S3 utility functions for image storage.
Uses IAM role-based authentication (no AWS keys needed).
Can fall back to local storage when DEBUG=True.
"""

import boto3
import io
import os
from flask import current_app
from botocore.exceptions import ClientError
from datetime import datetime
from PIL import Image as PILImage


def should_use_s3():
    """Check if S3 should be used based on deployment mode."""
    deployment_mode = current_app.config.get(
        'DEPLOYMENT_MODE',
        os.getenv('DEPLOYMENT_MODE', 'local')
    ).lower()

    bucket = current_app.config.get('S3_BUCKET_NAME')

    return deployment_mode == 'aws' and bool(bucket)


def get_s3_client():
    """Initialize S3 client using IAM role credentials"""
    return boto3.client(
        's3',
        region_name=current_app.config.get('AWS_REGION', 'us-east-1')
    )


def upload_image_to_s3(file, filename, bucket_name=None):
    """
    Upload image to S3 bucket OR local storage based on DEBUG setting.
    
    Args:
        file: Flask file object
        filename: Target filename in S3 or local
        bucket_name: S3 bucket name (uses config if not provided)
    
    Returns:
        S3 key (if S3) or local path (if DEBUG mode) on success, None on failure
    """
    # If DEBUG=True or no bucket configured, use local storage
    if not should_use_s3():
        return _upload_image_local(file, filename)
    
    # Otherwise use S3
    return _upload_image_s3(file, filename, bucket_name)


def _upload_image_local(file, filename):
    """Upload image to local filesystem (for development)"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # Open and validate image
        img = PILImage.open(file.stream)
        
        # Resize if too large
        max_width, max_height = 2000, 2000
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
        
        # Save optimized image
        filepath = os.path.join(upload_folder, filename)
        img.save(filepath, quality=85, optimize=True)
        
        # Return relative path for local storage
        return os.path.join('uploads', filename)
    
    except Exception as e:
        current_app.logger.error(f'Local upload error: {str(e)}')
        raise Exception(f'Failed to upload image locally: {str(e)}')


def _upload_image_s3(file, filename, bucket_name=None):
    """Upload image to S3 bucket with validation and optimization"""
    if bucket_name is None:
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME not configured')
    
    try:
        # Open and validate image
        img = PILImage.open(file.stream)
        
        # Resize if too large
        max_width, max_height = 2000, 2000
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
        
        # Save optimized image to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
        img_byte_arr.seek(0)
        
        # Upload to S3
        s3_client = get_s3_client()
        
        s3_key = f"images/{datetime.utcnow().strftime('%Y/%m/%d')}/{filename}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=img_byte_arr.getvalue(),
            ContentType='image/jpeg',
            ServerSideEncryption='AES256',  # Enable encryption
            Metadata={
                'original-name': filename,
                'uploaded-at': datetime.utcnow().isoformat()
            }
        )
        
        return s3_key
    
    except ClientError as e:
        current_app.logger.error(f'S3 upload error: {str(e)}')
        raise Exception(f'Failed to upload image to S3: {str(e)}')
    except Exception as e:
        current_app.logger.error(f'Image processing error: {str(e)}')
        raise Exception(f'Failed to process image: {str(e)}')


def delete_image_from_s3(s3_key, bucket_name=None):
    """
    Delete image from S3 bucket OR local storage based on storage mode.
    
    Args:
        s3_key: S3 object key or local path
        bucket_name: S3 bucket name (uses config if not provided)
    
    Returns:
        True on success, False on failure
    """
    # If DEBUG=True or no bucket, use local storage
    if not should_use_s3():
        return _delete_image_local(s3_key)
    
    # Otherwise use S3
    return _delete_image_s3(s3_key, bucket_name)


def _delete_image_local(local_path):
    """Delete image from local filesystem"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads')
        # Extract just the filename if full path given
        if '/' in local_path:
            filename = local_path.split('/')[-1]
        else:
            filename = local_path
        
        filepath = os.path.join(upload_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception as e:
        current_app.logger.error(f'Local delete error: {str(e)}')
        return False


def _delete_image_s3(s3_key, bucket_name=None):
    """Delete image from S3 bucket"""
    if bucket_name is None:
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME not configured')
    
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        return True
    except ClientError as e:
        current_app.logger.error(f'S3 delete error: {str(e)}')
        return False


def get_signed_url(s3_key, expiration=3600, bucket_name=None):
    """
    Generate signed URL for S3 object.
    Useful for private images - URL expires after specified time.
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration time in seconds (default: 1 hour)
        bucket_name: S3 bucket name (uses config if not provided)
    
    Returns:
        Signed URL on success, None on failure
    """
    if bucket_name is None:
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        return None
    
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        current_app.logger.error(f'Signed URL generation error: {str(e)}')
        return None


def check_s3_bucket_access(bucket_name=None):
    """
    Check if S3 bucket is accessible with current IAM role.
    
    Args:
        bucket_name: S3 bucket name (uses config if not provided)
    
    Returns:
        True if accessible, False otherwise
    """
    if bucket_name is None:
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        return False
    
    try:
        s3_client = get_s3_client()
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        current_app.logger.error(f'S3 bucket access error: {str(e)}')
        return False


def list_images_in_s3(prefix='images/', bucket_name=None):
    """
    List all images in S3 bucket (for debugging/cleanup).
    
    Args:
        prefix: S3 key prefix to filter results
        bucket_name: S3 bucket name (uses config if not provided)
    
    Returns:
        List of objects with key and metadata
    """
    if bucket_name is None:
        bucket_name = current_app.config.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        return []
    
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified']
                })
        
        return objects
    except ClientError as e:
        current_app.logger.error(f'S3 list error: {str(e)}')
        return []
