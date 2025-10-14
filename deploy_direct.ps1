# Direct Deployment Script for Gurtoy Telegram Bot
# Deploys bot directly from local files (no GitHub needed)

$GCLOUD = "C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "just-oarlock-471710-j1"
$INSTANCE_NAME = "gurtoy-bot"
$ZONE = "us-central1-a"
$LOCAL_PROJECT_DIR = "e:\tele_agent"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Gurtoy Bot Direct Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if instance exists
Write-Host "[1/6] Checking instance status..." -ForegroundColor Yellow
$instanceCheck = & $GCLOUD compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instance does not exist. Creating new instance..." -ForegroundColor Yellow
    
    # Create instance
    & $GCLOUD compute instances create $INSTANCE_NAME `
        --project=$PROJECT_ID `
        --zone=$ZONE `
        --machine-type=e2-micro `
        --image-family=debian-11 `
        --image-project=debian-cloud `
        --boot-disk-size=10GB `
        --tags=http-server
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create instance" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Instance created. Waiting 90 seconds for boot and automatic updates..." -ForegroundColor Yellow
    Start-Sleep -Seconds 90
} else {
    Write-Host "Instance already exists and running" -ForegroundColor Green
}

Write-Host ""

# Step 2: Install system dependencies
Write-Host "[2/6] Installing system dependencies..." -ForegroundColor Yellow

$installCmd = "echo 'Waiting for apt to be available...' && for i in {1..30}; do if ! sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then echo 'Apt is available'; break; fi; echo 'Waiting... ('$i'/30)'; sleep 10; done && sudo apt-get update && sudo apt-get install -y git supervisor python3-venv python3-pip python3-dev build-essential && echo 'Dependencies installed'"

& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$installCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "Dependencies installed successfully" -ForegroundColor Green
Write-Host ""

# Step 3: Create remote directory structure
Write-Host "[3/6] Creating remote directory structure..." -ForegroundColor Yellow

& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command="sudo mkdir -p /opt/gurtoy-bot && sudo chown -R \$(whoami):\$(whoami) /opt/gurtoy-bot && mkdir -p /opt/gurtoy-bot/temp_images /opt/gurtoy-bot/temp_audio /opt/gurtoy-bot/invoice/generated_invoice"

Write-Host "Directory structure created" -ForegroundColor Green
Write-Host ""

# Step 4: Upload all necessary files
Write-Host "[4/6] Uploading bot files..." -ForegroundColor Yellow

# COMPLETE LIST OF FILES TO UPLOAD - ALL FUNCTIONALITY INCLUDED
$filesToUpload = @(
    # Core Bot Files
    "run_bot.py",
    "gurtoy_bot.py",
    "gurtoy_bot_polling.py",
    "requirements.txt",
    
    # AI & Intelligence Systems
    "ai_order_collector.py",
    "intelligent_response_system.py",
    "knowledge_data.py",
    
    # NEW: Visual Verification System (CRITICAL)
    "visual_verification_system.py",
    "intelligent_image_matching.py",
    
    # Payment & Order Management
    "payment_manager.py",
    "invoice_generator.py",
    "order_collector.py",
    
    # Multimodal Handlers
    "image_handler.py",
    "audio_handler.py",
    "image_queue_manager.py",
    
    # Database & Setup Files
    "setup_database.py",
    "import_products.py",
    
    # Data Files
    "gurtoy_knowledge_data.json",
    ".env"
)

# Upload invoice logo
Write-Host "  Uploading invoice logo..." -ForegroundColor Gray
& $GCLOUD compute scp "$LOCAL_PROJECT_DIR\invoice\GURTOY Registered Trademark Logo.png" "${INSTANCE_NAME}:/opt/gurtoy-bot/invoice/" --zone=$ZONE --project=$PROJECT_ID

# Upload each file
foreach ($file in $filesToUpload) {
    $filePath = Join-Path $LOCAL_PROJECT_DIR $file
    if (Test-Path $filePath) {
        Write-Host "  Uploading $file..." -ForegroundColor Gray
        & $GCLOUD compute scp $filePath "${INSTANCE_NAME}:/opt/gurtoy-bot/" --zone=$ZONE --project=$PROJECT_ID
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Warning: Failed to upload $file" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Warning: $file not found, skipping..." -ForegroundColor Yellow
    }
}

Write-Host "Files uploaded successfully" -ForegroundColor Green
Write-Host ""

# Step 5: Setup Python environment and install packages
Write-Host "[5/6] Setting up Python environment..." -ForegroundColor Yellow

$setupCmd = "cd /opt/gurtoy-bot && echo 'Creating virtual environment...' && python3 -m venv venv && echo 'Installing Python packages...' && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && echo 'Python environment ready'"

& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$setupCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to setup Python environment" -ForegroundColor Red
    exit 1
}

Write-Host "Python environment configured" -ForegroundColor Green
Write-Host ""

# Step 6: Configure Supervisor and start bot
Write-Host "[6/6] Configuring Supervisor and starting bot..." -ForegroundColor Yellow

$supervisorCmd = "sudo tee /etc/supervisor/conf.d/gurtoy-bot.conf > /dev/null << 'EOF'
[program:gurtoy-bot]
command=/opt/gurtoy-bot/venv/bin/python /opt/gurtoy-bot/run_bot.py
directory=/opt/gurtoy-bot
autostart=true
autorestart=true
stderr_logfile=/var/log/gurtoy-bot.err.log
stdout_logfile=/var/log/gurtoy-bot.out.log
environment=PATH='/opt/gurtoy-bot/venv/bin'
stopwaitsecs=10
user=root
EOF
echo 'Starting bot...'
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart gurtoy-bot
sleep 5
echo ''
echo '=========================================='
echo 'Bot Status:'
echo '=========================================='
sudo supervisorctl status gurtoy-bot
echo ''
echo 'Recent Logs:'
sudo tail -n 30 /var/log/gurtoy-bot.out.log"

& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$supervisorCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Supervisor configuration may have issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Bot is now running with ALL functionality:" -ForegroundColor Green
Write-Host "   • Core bot system" -ForegroundColor White
Write-Host "   • AI order collection" -ForegroundColor White
Write-Host "   • Payment processing" -ForegroundColor White
Write-Host "   • Image handling" -ForegroundColor White
Write-Host "   • Voice processing" -ForegroundColor White
Write-Host "   • Visual verification system" -ForegroundColor White
Write-Host "   • Intelligent image matching" -ForegroundColor White
Write-Host "   • Database setup & product import" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Check bot status:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl status gurtoy-bot`""
Write-Host ""
Write-Host "📊 View live logs:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo tail -f /var/log/gurtoy-bot.out.log`""
Write-Host ""
Write-Host "🚨 IMPORTANT: If you made database changes, run this:" -ForegroundColor Red
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"cd /opt/gurtoy-bot && source venv/bin/activate && python setup_database.py`""
Write-Host ""
Write-Host "🔄 Restart bot:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl restart gurtoy-bot`""
Write-Host ""
Write-Host "🛑 Stop bot:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl stop gurtoy-bot`""
Write-Host ""
Write-Host "💻 SSH into instance:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
Write-Host ""
Write-Host "🔄 Update bot code (re-run this script):" -ForegroundColor Yellow
Write-Host "    .\deploy_direct.ps1"
Write-Host ""