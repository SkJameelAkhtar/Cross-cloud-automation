import subprocess
import datetime
import json
import time

RESOURCE_GROUP = "AZURE_RESOURCE_GROUP_PLACEHOLDER"
LOCATION = "AZURE_LOCATION_PLACEHOLDER"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

start_time = time.time()

# Step 1: Get latest snapshot

snap_cmd = f"az snapshot list -g {RESOURCE_GROUP} --query '[].name' -o tsv"
snapshots, _ = run_cmd(snap_cmd)

snap_list = [s for s in snapshots.split("\n") if s.startswith("backup-snap-")]
snap_list.sort()

if not snap_list:
    print("No snapshots found")
    exit()

latest_snapshot = snap_list[-1]
print("Using snapshot:", latest_snapshot)

timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")

disk_name = f"restore-disk-{timestamp}"
vm_name = f"restore-vm-{timestamp}"

# Step 2: Create disk

print("Creating disk...")
cmd = f"az disk create -g {RESOURCE_GROUP} -n {disk_name} --source {latest_snapshot}"
run_cmd(cmd)

# Step 3: Create VM

print("Creating VM...")
cmd = f"""
az vm create \
  --resource-group {RESOURCE_GROUP} \
  --name {vm_name} \
  --attach-os-disk {disk_name} \
  --os-type linux
"""
run_cmd(cmd)

# Step 4: Wait for VM
print("Waiting for VM to boot...")
time.sleep(60)

# Get public IP
ip_cmd = f"az vm list-ip-addresses -g {RESOURCE_GROUP} -n {vm_name} --query '[0].virtualMachine.network.publicIpAddresses[0].ipAddress' -o tsv"
ip, _ = run_cmd(ip_cmd)

print("VM IP:", ip)

# Step 5: Validate app
print("Validating app...")
validate_cmd = f"curl -s http://{ip}:5000/read"
output, err = run_cmd(validate_cmd)

if "Entry" in output:
    status = "SUCCESS"
else:
    status = "FAILED"

# Step 6: Measure time
end_time = time.time()
recovery_time = round(end_time - start_time, 2)

# Step 7: Log result
log = {
    "type": "recovery",
    "time": str(datetime.datetime.utcnow()),
    "status": status,
    "snapshot_used": latest_snapshot,
    "vm_name": vm_name,
    "ip": ip,
    "recovery_time_sec": recovery_time
}

with open("recovery_log.json", "a") as f:
    f.write(json.dumps(log) + "\n")

print("Recovery Log:", log)

# Step 8: Cleanup (VERY IMPORTANT)
print("Cleaning up...")

run_cmd(f"az vm delete -g {RESOURCE_GROUP} -n {vm_name} --yes")
run_cmd(f"az disk delete -g {RESOURCE_GROUP} -n {disk_name} --yes")

print("Cleanup done.")
