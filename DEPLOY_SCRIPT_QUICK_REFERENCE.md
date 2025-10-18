# Fashion Mart Bot - Deployment Script Quick Reference

## 🚀 Quick Start

```powershell
# Deploy (creates instance if needed, reuses if exists)
.\deploy_gcloud_fresh.ps1
```

That's it! The script handles everything.

---

## 📊 Instance Behavior

### First Run
```
[1/8] Checking instance status...
[INFO] Instance does not exist. Creating new instance...
[OK] Instance created
[INFO] Waiting 90 seconds for instance to boot...
```
**Time: ~20 minutes** (includes boot time)

### Second Run (or later)
```
[1/8] Checking instance status...
[OK] Instance already exists and running
```
**Time: ~10-15 minutes** (no boot wait)

---

## 🔧 Instance Details

| Setting | Value |
|---------|-------|
| **Instance Name** | `fashion-mart-bot` |
| **Region** | `us-central1-a` |
| **Machine Type** | `e2-medium` |
| **OS** | Debian 11 |
| **Bot Directory** | `/opt/fashion-mart-bot` |
| **Project ID** | `just-oarlock-471710-j1` |

---

## 📋 What Gets Deployed

### Python Files (18 files)
- `run_bot.py` - Main entry point
- `gurtoy_bot.py` - Bot logic
- `gurtoy_bot_polling.py` - Polling mode
- `knowledge_data.py` - Fashion Mart knowledge base
- `ai_order_collector.py` - Order processing
- `intelligent_response_system.py` - AI responses
- `intelligent_image_matching.py` - Image recognition
- `visual_verification_system.py` - Image verification
- `payment_manager.py` - Payment processing
- `invoice_generator.py` - Invoice creation
- `order_collector.py` - Order management
- `image_handler.py` - Image processing
- `audio_handler.py` - Voice processing
- `image_queue_manager.py` - Image queue
- `setup_database.py` - Database initialization
- `import_products.py` - Product import
- `.env` - Configuration
- `requirements.txt` - Python dependencies
- `supabase_schema.sql` - Database schema

### Features
✅ Core bot system
✅ AI order collection
✅ Payment processing
✅ Image handling (product photos)
✅ Voice processing (audio messages)
✅ Visual verification
✅ Intelligent image matching
✅ Database with embeddings
✅ Product management

---

## 🟢 Verify Bot is Running

### Check Status
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl status fashion-mart-bot"
```

**Expected Output:**
```
fashion-mart-bot                 RUNNING   pid 1234, uptime 0:00:45
```

### View Live Logs
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo tail -f /var/log/fashion-mart-bot.out.log"
```

### SSH into Instance
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a
```

---

## 🔄 Common Operations

### Restart Bot
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl restart fashion-mart-bot"
```

### Stop Bot
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl stop fashion-mart-bot"
```

### Start Bot
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl start fashion-mart-bot"
```

### Update Bot Code
```powershell
# Re-run deployment script (same code gets uploaded and bot restarts)
.\deploy_gcloud_fresh.ps1
```

### Update Database
```powershell
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python setup_database.py"
```

---

## 🐛 Troubleshooting

### Bot not running?
```powershell
# Check status
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl status fashion-mart-bot"

# If stopped, restart
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="sudo supervisorctl restart fashion-mart-bot"
```

### Instance creation failed?
```powershell
# Check quotas
gcloud compute instances list

# Verify project and zone are correct
# Check GCP console for any restrictions
```

### File upload failed?
```powershell
# Check if files exist locally
Test-Path e:\github\agent\run_bot.py

# Check remote directory
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="ls -la /opt/fashion-mart-bot/"
```

### Python environment issues?
```powershell
# Reinstall dependencies
gcloud compute ssh fashion-mart-bot --zone=us-central1-a --command="cd /opt/fashion-mart-bot && source venv/bin/activate && pip install -r requirements.txt"
```

---

## 📈 Instance Costs

- **Machine Type**: `e2-medium`
- **CPU**: 1 vCPU
- **Memory**: 4 GB RAM
- **Boot Disk**: 20 GB SSD
- **Estimated Monthly Cost**: $2-4 USD

---

## ⏱️ Deployment Timeline

```
Step 1: Check/Create Instance        [1-2 min]
        └─ If new: wait 90 seconds   [1.5 min]

Step 2: Install Dependencies         [3-5 min]
Step 3: Create Directories           [0.5 min]
Step 4: Upload Files                 [2-3 min]
Step 5: Setup Python & Packages      [8-10 min]
Step 6: Initialize Database          [2-3 min]
Step 7: Configure Supervisor         [2-3 min]
Step 8: Status Report                [0.5 min]

─────────────────────────────
TOTAL (new instance)         ≈ 20-25 minutes
TOTAL (existing instance)    ≈ 10-15 minutes
```

---

## 🔐 Security Notes

- Bot runs with root privileges (supervised)
- Use `.env` file for sensitive credentials
- Keep `.env` backed up securely
- Don't commit `.env` to version control

---

## 📞 Help Commands

```powershell
# List all instances
gcloud compute instances list

# List specific instance
gcloud compute instances describe fashion-mart-bot --zone=us-central1-a

# SSH into instance
gcloud compute ssh fashion-mart-bot --zone=us-central1-a

# View instance details
gcloud compute instances describe fashion-mart-bot --zone=us-central1-a --format=yaml
```

---

*Version: 1.0*
*Last Updated: 2025-10-18*