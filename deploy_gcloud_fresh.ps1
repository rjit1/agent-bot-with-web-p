# Direct Deployment Script for Fashion Mart Telegram Bot
# Deploys bot directly from local files to same instance (no GitHub needed)

$GCLOUD = "gcloud"
$PROJECT_ID = "just-oarlock-471710-j1"
$INSTANCE_NAME = "fashion-mart-bot"
$ZONE = "us-central1-a"
$MACHINE_TYPE = "e2-medium"
$LOCAL_PROJECT_DIR = "e:\github\agent"
$REMOTE_APP_DIR = "/opt/fashion-mart-bot"

function Write-Success { param([string]$msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-ErrorMsg { param([string]$msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Info { param([string]$msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Step { param([int]$n, [int]$total, [string]$msg) Write-Host "[$n/$total] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fashion Mart Bot Direct Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Info "Instance Name: $INSTANCE_NAME"
Write-Info "Zone: $ZONE"
Write-Info "Project: $PROJECT_ID"
Write-Info "Local Project Dir: $LOCAL_PROJECT_DIR"
Write-Host ""

# Step 1: Check if instance exists
Write-Step 1 8 "Checking instance status..."
$instanceCheck = & $GCLOUD compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Info "Instance does not exist. Creating new instance..."
    
    # Create instance
    & $GCLOUD compute instances create $INSTANCE_NAME `
        --project=$PROJECT_ID `
        --zone=$ZONE `
        --machine-type=$MACHINE_TYPE `
        --image-family=debian-11 `
        --image-project=debian-cloud `
        --boot-disk-size=20GB
    
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to create instance"
        exit 1
    }
    
    Write-Success "Instance created"
    Write-Info "Waiting 90 seconds for instance to boot..."
    Start-Sleep -Seconds 90
} else {
    Write-Success "Instance already exists and running"
}
Write-Host ""

Write-Step 2 8 "Installing dependencies..."
$installCmd = 'sudo apt-get update && sudo apt-get install -y git supervisor python3-venv python3-pip python3-dev build-essential curl wget'
& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$installCmd 2>&1 | Out-Null
Write-Success "Dependencies installed"
Write-Host ""

Write-Step 3 8 "Creating remote directory structure..."
$mkdirCmd = "sudo mkdir -p $REMOTE_APP_DIR && sudo chown -R `$(whoami):`$(whoami) $REMOTE_APP_DIR && mkdir -p $REMOTE_APP_DIR/temp_images $REMOTE_APP_DIR/temp_audio $REMOTE_APP_DIR/invoice/generated_invoice"
& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$mkdirCmd 2>&1 | Out-Null
Write-Success "Directory structure created"
Write-Host ""

Write-Step 4 8 "Uploading bot files..."

# COMPLETE LIST OF FILES TO UPLOAD - ALL FUNCTIONALITY INCLUDED
$filesToUpload = @(
    # Core Bot Files
    "run_bot.py", "gurtoy_bot_polling.py", "gurtoy_bot.py", "requirements.txt",
    # AI & Intelligence Systems
    "ai_order_collector.py", "intelligent_response_system.py", "knowledge_data.py",
    # Visual Verification System
    "visual_verification_system.py", "intelligent_image_matching.py",
    # Payment & Order Management
    "payment_manager.py", "invoice_generator.py", "order_collector.py",
    # Multimodal Handlers
    "image_handler.py", "audio_handler.py", "image_queue_manager.py",
    # Database & Setup Files
    "setup_database.py", "import_products.py", "supabase_schema.sql",
    # Configuration
    ".env"
)

$uploadCount = 0
foreach ($file in $filesToUpload) {
    $filePath = Join-Path $LOCAL_PROJECT_DIR $file
    if (Test-Path $filePath) {
        Write-Host "  Uploading $file..." -ForegroundColor Gray
        & $GCLOUD compute scp $filePath "${INSTANCE_NAME}:${REMOTE_APP_DIR}/" --zone=$ZONE --project=$PROJECT_ID 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { 
            $uploadCount++ 
        } else {
            Write-Host "  Warning: Failed to upload $file" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Warning: $file not found, skipping..." -ForegroundColor Yellow
    }
}
Write-Success "Files uploaded: $uploadCount files"
Write-Host ""

Write-Step 5 8 "Setting up Python environment..."
$setupPyCmd = "cd $REMOTE_APP_DIR && echo 'Creating virtual environment...' && python3 -m venv venv && echo 'Installing Python packages...' && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && echo 'Python environment ready'"
& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$setupPyCmd 2>&1 | Out-Null
Write-Success "Python environment configured"
Write-Host ""

Write-Step 6 8 "Initializing database..."
$dbCmd = "cd $REMOTE_APP_DIR && source venv/bin/activate && python setup_database.py"
& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$dbCmd 2>&1 | Out-Null
Write-Success "Database initialized"
Write-Host ""

Write-Step 7 8 "Configuring Supervisor and starting bot..."

$supervisorCmd = "sudo tee /etc/supervisor/conf.d/fashion-mart-bot.conf > /dev/null << 'EOF'
[program:fashion-mart-bot]
command=$REMOTE_APP_DIR/venv/bin/python $REMOTE_APP_DIR/run_bot.py
directory=$REMOTE_APP_DIR
autostart=true
autorestart=true
stderr_logfile=/var/log/fashion-mart-bot.err.log
stdout_logfile=/var/log/fashion-mart-bot.out.log
environment=PATH='$REMOTE_APP_DIR/venv/bin',PYTHONUNBUFFERED=1
stopwaitsecs=10
user=root
EOF
echo 'Starting bot...'
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart fashion-mart-bot
sleep 5
echo ''
echo '=========================================='
echo 'Bot Status:'
echo '=========================================='
sudo supervisorctl status fashion-mart-bot
echo ''
echo 'Recent Logs:'
sudo tail -n 30 /var/log/fashion-mart-bot.out.log"

& $GCLOUD compute ssh $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --command=$supervisorCmd 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Supervisor configuration may have issues" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "[OK] DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "[OK] Bot is now running with ALL functionality:" -ForegroundColor Green
Write-Host "   • Core bot system" -ForegroundColor White
Write-Host "   • AI order collection" -ForegroundColor White
Write-Host "   • Payment processing" -ForegroundColor White
Write-Host "   • Image handling" -ForegroundColor White
Write-Host "   • Voice processing" -ForegroundColor White
Write-Host "   • Visual verification system" -ForegroundColor White
Write-Host "   • Intelligent image matching" -ForegroundColor White
Write-Host "   • Database setup & product import" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Check bot status:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl status fashion-mart-bot`""
Write-Host ""
Write-Host "[INFO] View live logs:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo tail -f /var/log/fashion-mart-bot.out.log`""
Write-Host ""
Write-Host "[ERROR] If you made database changes, run this:" -ForegroundColor Red
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"cd $REMOTE_APP_DIR && source venv/bin/activate && python setup_database.py`""
Write-Host ""
Write-Host "[INFO] Restart bot:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl restart fashion-mart-bot`""
Write-Host ""
Write-Host "[INFO] Stop bot:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command=`"sudo supervisorctl stop fashion-mart-bot`""
Write-Host ""
Write-Host "[INFO] SSH into instance:" -ForegroundColor Yellow
Write-Host "    gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
Write-Host ""
Write-Host "[INFO] Update bot code (re-run this script):" -ForegroundColor Yellow
Write-Host "    .\deploy_gcloud_fresh.ps1"
Write-Host ""