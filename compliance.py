import json
import datetime
import boto3
import smtplib
from email.mime.text import MIMEText
from azure.storage.blob import BlobServiceClient

# ---------------- CONFIG ----------------
AZURE_CONNECTION_STRING = "AZURE_STORAGE_CONNECTION_STRING_PLACEHOLDER"
AZURE_CONTAINER = "AZURE_CONTAINER_NAME_PLACEHOLDER"
S3_BUCKET = "S3_BUCKET_NAME_PLACEHOLDER"

EMAIL_SENDER = "EMAIL_SENDER_PLACEHOLDER"
EMAIL_PASSWORD = "EMAIL_PASSWORD_PLACEHOLDER"
EMAIL_RECEIVER = "EMAIL_RECEIVER_PLACEHOLDER"

# ----------------------------------------

def calculate_metrics(logs):
    backups = [l for l in logs if l.get("type") == "backup"]
    recoveries = [l for l in logs if l.get("type") == "recovery"]

    # Backup success rate
    if backups:
        backup_success_rate = sum(1 for b in backups if b["status"] == "SUCCESS") / len(backups) * 100
    else:
        backup_success_rate = 0

    # Restore success rate
    if recoveries:
        restore_success_rate = sum(1 for r in recoveries if r["status"] == "SUCCESS") / len(recoveries) * 100
    else:
        restore_success_rate = 0

    # Recovery validation time (avg)
    recovery_times = [r.get("recovery_time_sec", 0) for r in recoveries if r["status"] == "SUCCESS"]
    avg_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0

    # Compliance report completeness
    required_fields = ["time", "status"]
    completeness_scores = []

    for log in logs:
        present = sum(1 for f in required_fields if f in log)
        completeness_scores.append(present / len(required_fields))

    compliance_completeness = sum(completeness_scores) / len(completeness_scores) * 100 if logs else 0

    # Automation coverage (simple version)
    automated_jobs = len(backups) + len(recoveries)
    automation_coverage = min(100, automated_jobs * 10)  # scaled for demo

    # Error handling quality
    errors = [l for l in logs if l.get("status") == "FAILED"]
    error_handling_quality = 100 - (len(errors) / len(logs) * 100 if logs else 0)

    return {
        "backup_success_rate": round(backup_success_rate, 2),
        "restore_success_rate": round(restore_success_rate, 2),
        "avg_recovery_time_sec": round(avg_recovery_time, 2),
        "compliance_completeness": round(compliance_completeness, 2),
        "automation_coverage": round(automation_coverage, 2),
        "error_handling_quality": round(error_handling_quality, 2)
    }

def log_event(message):
    with open("system.log", "a") as f:
        f.write(f"{datetime.datetime.utcnow()} - {message}\n")

def fetch_from_blob():
    logs = []
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        container = blob_service.get_container_client(AZURE_CONTAINER)

        for blob in container.list_blobs():
            data = container.download_blob(blob.name).readall()
            logs.append(json.loads(data))
    except Exception as e:
        log_event(f"Azure fetch error: {e}")
    return logs

def fetch_from_s3():
    logs = []
    try:
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=S3_BUCKET)

        if "Contents" in response:
            for obj in response["Contents"]:
                file = s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
                data = file["Body"].read()
                logs.append(json.loads(data))
    except Exception as e:
        log_event(f"S3 fetch error: {e}")
    return logs

def evaluate_compliance(logs):
    now = datetime.datetime.utcnow()
    success = [l for l in logs if l["status"] == "SUCCESS"]

    # Rules
    recent_backup = any(
        (now - datetime.datetime.fromisoformat(l["time"])).total_seconds() < 86400
        for l in success
    )

    enough_backups = len(success) >= 3

    # Placeholder (you’ll plug recovery later)
    recovery_success = True

    checklist = {
        "ISO_27001_Backup_Policy": recent_backup,
        "NIST_CP_9_Backup": enough_backups,
        "CIS_Recovery_Test": recovery_success
    }

    compliance_score = round(
        sum(checklist.values()) / len(checklist) * 100, 2
    )

    return checklist, compliance_score

def generate_html(checklist, score):
    rows = ""
    for k, v in checklist.items():
        status = "✅ PASS" if v else "❌ FAIL"
        rows += f"<tr><td>{k}</td><td>{status}</td></tr>"

    html = f"""
    <html>
    <body>
        <h1>Compliance Report</h1>
        <h2>Score: {score}%</h2>
        <table border="1">
            <tr><th>Control</th><th>Status</th></tr>
            {rows}
        </table>
    </body>
    </html>
    """
    return html

def send_email(html, subject):
    try:
        msg = MIMEText(html, "html")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()

        log_event("Email sent successfully")
    except Exception as e:
        log_event(f"Email error: {e}")

# ---------------- MAIN ----------------

log_event("Starting compliance job")

blob_logs = fetch_from_blob()
s3_logs = fetch_from_s3()
all_logs = blob_logs + s3_logs

checklist, score = evaluate_compliance(all_logs)

# Save JSON report
report = {
    "timestamp": str(datetime.datetime.utcnow()),
    "score": score,
    "controls": checklist
}

with open("report.json", "w") as f:
    json.dump(report, f, indent=4)

# Save HTML report
html = generate_html(checklist, score)
with open("report.html", "w") as f:
    f.write(html)

log_event(f"Report generated with score {score}%")

# ALERTING LOGIC
if score < 100:
    send_email(html, "🚨 Compliance Alert: Issues Detected")
else:
    send_email(html, "✅ Compliance Report: All Good")

metrics = calculate_metrics(all_logs)

report = {
    "timestamp": str(datetime.datetime.utcnow()),
    "score": score,
    "controls": checklist,
    "metrics": metrics
}
