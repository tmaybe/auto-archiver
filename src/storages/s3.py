
from typing import IO, Any
import boto3, uuid, os, mimetypes
from botocore.errorfactory import ClientError
from metadata import Metadata
from media import Media
from storages import StorageV2
from loguru import logger
from slugify import slugify


class S3StorageV2(StorageV2):
    name = "s3_storage"

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.s3 = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint_url.format(region=self.region),
            aws_access_key_id=self.key,
            aws_secret_access_key=self.secret
        )

    @staticmethod
    def configs() -> dict:
        return {
            "bucket": {"default": None, "help": "S3 bucket name"},
            "region": {"default": None, "help": "S3 region name"},
            "key": {"default": None, "help": "S3 API key"},
            "secret": {"default": None, "help": "S3 API secret"},
            # TODO: how to have sth like a custom folder? has to come from the feeders
            "endpoint_url": {
                "default": 'https://{region}.digitaloceanspaces.com',
                "help": "S3 bucket endpoint, {region} are inserted at runtime"
            },
            "cdn_url": {
                "default": 'https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}',
                "help": "S3 CDN url, {bucket}, {region} and {key} are inserted at runtime"
            },
            "private": {"default": False, "help": "if true S3 files will not be readable online"},
            # "key_path": {"default": "random", "help": "S3 file names are non-predictable strings, one of ['random', 'default']"},
        }

    def get_cdn_url(self, media: Media) -> str:
        return self.cdn_url.format(bucket=self.bucket, region=self.region, key=media.key)

    def uploadf(self, file: IO[bytes], media: Media, **kwargs: dict) -> Any:
        extra_args = kwargs.get("extra_args", {})
        if not self.private and 'ACL' not in extra_args:
            extra_args['ACL'] = 'public-read'

        if 'ContentType' not in extra_args:
            try:
                extra_args['ContentType'] = mimetypes.guess_type(media.key)[0]
            except Exception as e:
                logger.warning(f"Unable to get mimetype for {media.key=}, error: {e}")

        self.s3.upload_fileobj(file, Bucket=self.bucket, Key=media.key, ExtraArgs=extra_args)

    def exists(self, key: str) -> bool:
        """
        Tests if a given file with key=key exists in the bucket
        """
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            logger.warning(f"got a ClientError when checking if {key=} exists in bucket={self.bucket}: {e}")
        return False
