import subprocess
import datetime
import json
import os
import boto3
from azure.storage.blob import BlobServiceClient

RESOURCE_GROUP = "AZURE_RESOURCE_GROUP_PLACEHOLDER"
VM_NAME = "VM_NAME_PLACEHOLDER"

# CONFIG
AZURE_CONNECTION_STRING = "AZURE_STORAGE_CONNECTION_STRING_PLACEHOLDER"
AZURE_CONTAINER = "AZURE_CONTAINER_NAME_PLACEHOLDER"
S3_BUCKET = "S3_BUCKET_NAME_PLACEHOLDER"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

# Get disk ID
disk_cmd = f"az vm show -g {RESOURCE_GROUP} -n {VM_NAME} --query 'storageProfile.osDisk.managedDisk.id' -o tsv"
disk_id, err = run_cmd(disk_cmd)

timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
snapshot_name = f"backup-snap-{timestamp}"

# Create snapshot
snap_cmd = f"az snapshot create --resource-group {RESOURCE_GROUP} --source {disk_id} --name {snapshot_name}"
out, err = run_cmd(snap_cmd)

# Metadata
log = {
    "time": str(datetime.datetime.utcnow()),
    "snapshot": snapshot_name,
    "status": "SUCCESS" if not err else "FAILED",
    "error": err
}

# Save locally
filename = f"metadata_{timestamp}.json"
with open(filename, "w") as f:
    json.dump(log, f, indent=4)

print("Saved locally:", filename)

# Upload to Azure Blob

try:
    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER, blob=filename)

    with open(filename, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    print("Uploaded to Azure Blob")
except Exception as e:
    print("Azure upload failed:", e)

# Upload to AWS S3

try:
    s3 = boto3.client("s3")
    s3.upload_file(filename, S3_BUCKET, filename)
    print("Uploaded to AWS S3")
except Exception as e:
    print("S3 upload failed:", e)
