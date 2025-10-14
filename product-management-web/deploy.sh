#!/bin/bash

# Product Management Web App - Deployment Script
# This script helps deploy the Next.js application

echo "🚀 Product Management Web App - Deployment Script"
echo "=================================================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Node.js and npm are installed"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  .env.local not found. Creating from template..."
    cp env.example .env.local
    echo "📝 Please update .env.local with your Supabase credentials"
    echo "   Required variables:"
    echo "   - NEXT_PUBLIC_SUPABASE_URL"
    echo "   - NEXT_PUBLIC_SUPABASE_ANON_KEY"
    echo "   - SUPABASE_SERVICE_ROLE_KEY"
    echo "   - JWT_SECRET"
    echo ""
    echo "   Default password is already set to: 121233"
    echo ""
    read -p "Press Enter after updating .env.local..."
fi

# Build the application
echo "🔨 Building application..."
npm run build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "🚀 To start the application:"
    echo "   npm start"
    echo ""
    echo "🌐 Application will be available at:"
    echo "   http://localhost:3000"
    echo ""
    echo "🔐 Login with password: 121233"
    echo ""
    echo "📱 Mobile-friendly interface included!"
else
    echo "❌ Build failed. Please check the errors above."
    exit 1
fi
