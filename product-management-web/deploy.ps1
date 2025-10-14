# Product Management Web App - Deployment Script (PowerShell)
# This script helps deploy the Next.js application

Write-Host "🚀 Product Management Web App - Deployment Script" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if Node.js is installed
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js is installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not installed. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Check if npm is installed
try {
    $npmVersion = npm --version
    Write-Host "✅ npm is installed: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ npm is not installed. Please install npm first." -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Check if .env.local exists
if (-not (Test-Path ".env.local")) {
    Write-Host "⚠️  .env.local not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item "env.example" ".env.local"
    Write-Host "📝 Please update .env.local with your Supabase credentials" -ForegroundColor Cyan
    Write-Host "   Required variables:" -ForegroundColor Cyan
    Write-Host "   - NEXT_PUBLIC_SUPABASE_URL" -ForegroundColor Cyan
    Write-Host "   - NEXT_PUBLIC_SUPABASE_ANON_KEY" -ForegroundColor Cyan
    Write-Host "   - SUPABASE_SERVICE_ROLE_KEY" -ForegroundColor Cyan
    Write-Host "   - JWT_SECRET" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Default password is already set to: 121233" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter after updating .env.local"
}

# Build the application
Write-Host "🔨 Building application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 To start the application:" -ForegroundColor Cyan
    Write-Host "   npm start" -ForegroundColor White
    Write-Host ""
    Write-Host "🌐 Application will be available at:" -ForegroundColor Cyan
    Write-Host "   http://localhost:3000" -ForegroundColor White
    Write-Host ""
    Write-Host "🔐 Login with password: 121233" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📱 Mobile-friendly interface included!" -ForegroundColor Cyan
} else {
    Write-Host "❌ Build failed. Please check the errors above." -ForegroundColor Red
    exit 1
}
