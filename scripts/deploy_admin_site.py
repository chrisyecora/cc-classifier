"""Build-time config and S3 upload for the static admin page."""

import argparse
import json
from pathlib import Path

import boto3


def deploy(stack_name: str, dist: Path):
    cf = boto3.client("cloudformation")
    outputs = {
        item["OutputKey"]: item["OutputValue"]
        for item in cf.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    }
    config = {
        "userPoolId": outputs["AdminUserPoolId"],
        "userPoolClientId": outputs["AdminUserPoolClientId"],
        "cognitoDomain": outputs["AdminCognitoDomain"],
        "redirectUrl": outputs["AdminSiteUrl"],
    }
    (dist / "config.json").write_text(json.dumps(config), encoding="utf-8")
    s3 = boto3.client("s3")
    bucket = outputs["AdminSiteBucketName"]
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(dist).as_posix()
        content_type = {
            ".html": "text/html",
            ".js": "text/javascript",
            ".css": "text/css",
            ".json": "application/json",
        }.get(path.suffix, "application/octet-stream")
        s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type, "CacheControl": "no-store"})
    print(outputs["AdminSiteUrl"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack-name", required=True)
    parser.add_argument("--dist", type=Path, default=Path("web/dist"))
    args = parser.parse_args()
    deploy(args.stack_name, args.dist)
