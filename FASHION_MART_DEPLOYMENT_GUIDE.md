# 🚀 Fashion Mart Telegram Bot - Fresh Deployment Guide

**Status**: Complete Migration from Toy Niche → Fashion Niche ✅

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Current Directory Structure](#directory-structure)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Fresh Instance Setup](#fresh-instance-setup)
5. [Deployment Methods](#deployment-methods)
6. [Verification & Testing](#verification--testing)
7. [Post-Deployment Configuration](#post-deployment-configuration)

---

## 📁 Project Overview

**Working Directory**: `e:\github\agent`

**Project**: Fashion Mart Telegram Bot (Phase 8 - Complete Migration)

**Key Components**:
- 🤖 **Bot**: `gurtoy_bot_polling.py` (polling mode - no webhook required)
- 🎯 **Core Bot**: `gurtoy_bot.py` (webhook mode)
- 🧠 **AI System**: Gemini 2.5 Flash with vector search
- 💾 **Database**: Supabase with PostgreSQL + pgvector
- 📦 **Knowledge Base**: Fashion Mart product & contact info
- 💳 **Payment System**: Razorpay integration (optional)
- 🖼️ **Multimodal**: Image & audio handling

---

## 📂 Directory Structure

```
e:\github\agent/
├── Core Bot Files
│   ├── gurtoy_bot_polling.py          ← Polling mode launcher (RECOMMENDED for NEW instance)
│   ├── gurtoy_bot.py                  ← Webhook mode (advanced)
│   ├── run_bot.py                     ← Polling bot launcher script
│   
├── Configuration & Setup
│   ├── .env                           ← CRITICAL: Environment variables
│   ├── .env.example                   ← Template
│   ├── requirements.txt               ← Python dependencies
│   ├── setup_database.py              ← Database initialization
│   
├── AI & Intelligence
│   ├── knowledge_data.py              ← Fashion knowledge chunks (FASHION NICHE)
│   ├── gurtoy_knowledge_data.json     ← Generated embeddings file
│   ├── intelligent_response_system.py ← Response generation
│   
├── Order & Payment
│   ├── ai_order_collector.py          ← Order collection AI
│   ├── payment_manager.py             ← Razorpay integration
│   ├── invoice_generator.py           ← Invoice PDF generation
│   
├── Multimodal Handlers
│   ├── image_handler.py               ← Image processing
│   ├── audio_handler.py               ← Audio processing
│   ├── visual_verification_system.py  ← Fashion image verification
│   ├── intelligent_image_matching.py  ← AI image matching
│   
├── Database
│   ├── supabase_schema.sql            ← Database schema
│   
├── Deployment
│   ├── deploy_direct.ps1              ← OLD: Direct deployment (for existing instance)
│   ├── deploy_gcloud_fresh.ps1        ← NEW: Fresh GCP instance deployment
│   
└── Documentation & Logs
    ├── README.md
    ├── temp_images/                   ← Temporary storage
    ├── temp_audio/                    ← Temporary storage
    └── invoice/generated_invoice/     ← Invoice PDFs
```

---

## ✅ Pre-Deployment Checklist

### 1. Environment Configuration (.env)
- ✅ **GEMINI_API_KEY**: Google AI Studio API key
- ✅ **TELEGRAM_BOT_TOKEN**: Telegram bot token
- ✅ **SUPABASE_URL**: Supabase project URL
- ✅ **SUPABASE_SERVICE_ROLE_KEY**: Service role key
- ✅ **RAZORPAY_KEY_ID**: Razorpay test/live key (optional)
- ✅ **RAZORPAY_KEY_SECRET**: Razorpay secret (optional)
- ✅ **Business Settings**: Address, phone, email (Fashion Mart configured)

**Current .env Status**: ✅ READY for Fashion Mart

```env
GEMINI_API_KEY=AIzaSyB1yfhAcsXvr5wM9u2oAigZTp0uWQRt27Q
TELEGRAM_BOT_TOKEN=7504641562:AAEm8-Au1d7rk9d8yJLeASnkQJuDQ6y6M7s
SUPABASE_URL=https://uejyfpzabmlrgkdayfrn.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
BUSINESS_ADDRESS="PLOT NO. B/31/1097/1, NEAR CHURCH... (Fashion Mart)"
BUSINESS_PHONE_INQUIRY="9876151585"
BUSINESS_PHONE_BUY="6283837649"
```

### 2. Python & Dependencies
- ✅ Python 3.9+ required
- ✅ requirements.txt includes all dependencies
- ✅ Virtual environment ready for fresh setup

### 3. Database
- ✅ Supabase project created
- ✅ PostgreSQL with pgvector extension enabled
- ✅ Schema prepared (supabase_schema.sql)

### 4. Knowledge Base
- ✅ knowledge_data.py contains FASHION MART knowledge (NOT toy niche)
- ✅ gurtoy_knowledge_data.json will be generated during setup

### 5. API Keys & Services
- ✅ Gemini API: Active
- ✅ Telegram Bot: Created (token in .env)
- ✅ Supabase: Project ready
- ✅ Razorpay: Optional (for payments)

---

## 🆕 Fresh Instance Setup

### Option A: Local Development (QUICK - No Cloud Required)

Perfect for testing before cloud deployment!

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup database (one-time)
python setup_database.py

# 3. Run bot (polling mode - no webhook needed)
python run_bot.py
```

**Result**: Bot running locally on your machine
- No ngrok needed
- No webhook setup required
- Perfect for development & testing
- Message delay: 1-2 seconds (acceptable for non-production)

### Option B: Google Cloud Platform (PRODUCTION)

#### Step 1: Create New GCP Instance

```bash
# Using the new fresh deployment script
.\deploy_gcloud_fresh.ps1
```

**Script will**:
1. ✅ Create NEW GCP instance (not reuse existing)
2. ✅ Install system dependencies
3. ✅ Set up Python virtual environment
4. ✅ Upload all bot files
5. ✅ Generate knowledge embeddings
6. ✅ Initialize database
7. ✅ Start bot with Supervisor

#### Step 2: Manual GCP Setup (if script not used)

```bash
# SSH into instance
gcloud compute ssh INSTANCE_NAME --zone=us-central1-a --project=PROJECT_ID

# Setup steps
cd /opt/fashion-mart-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python setup_database.py
python run_bot.py
```

---

## 🚀 Deployment Methods

### Method 1: Polling Mode (RECOMMENDED for NEW instance)

**Best for**: 
- Fresh deployments
- No webhook complexity
- Development & testing
- Instant setup

**Launch**:
```bash
python run_bot.py
```

**How it works**:
- Bot polls Telegram API for new messages
- No public URL required
- No ngrok needed
- Works on any machine

**Advantages**:
✅ Simple setup
✅ No infrastructure required
✅ Perfect for testing
✅ No webhook issues

**Disadvantages**:
⚠️ 1-2 second message delay
⚠️ Slightly higher resource usage

---

### Method 2: Webhook Mode (Advanced - Production)

**Best for**:
- Production deployment
- High message volume
- Real-time requirements

**Setup**:
```bash
# Start FastAPI server
python gurtoy_bot.py

# In another terminal, setup webhook
python deploy_bot.py
```

**How it works**:
- Telegram sends messages to your webhook URL
- Instant delivery
- Lower resource usage

**Advantages**:
✅ Instant message delivery
✅ Lower resource usage
✅ Better for high traffic

**Disadvantages**:
⚠️ Requires public URL
⚠️ Requires webhook setup
⚠️ More complex deployment

---

## 🔍 Verification & Testing

### 1. Verify Connections

```python
# Check all systems ready
python -c "from gurtoy_bot import config, logger; logger.info('✅ Bot ready to start')"
```

### 2. Test Database Setup

```bash
python setup_database.py
```

Expected output:
```
🔧 Initializing clients...
✅ Gemini API connection successful
✅ Supabase connection successful
📚 Loading knowledge data...
✅ Loaded 15+ knowledge chunks
🧠 Generating embeddings...
✅ Embeddings generated successfully
✅ Database setup complete!
```

### 3. Test Bot Responses

Once running, send messages in Telegram:

**Test Message 1**: "What's your address?" 
- Expected: Fashion Mart address response

**Test Message 2**: "Show me cardigans"
- Expected: Product recommendations with Fashion Mart knowledge

**Test Message 3**: "Call me"
- Expected: Contact information with Fashion Mart details

**Test Message 4**: "I want to order something"
- Expected: Order collection flow starts (if payment system enabled)

### 4. Check Logs

```bash
# View bot logs
tail -f /var/log/gurtoy-bot.out.log

# Or locally
# Logs appear in console output with timestamps
```

---

## 📝 Post-Deployment Configuration

### 1. Verify Fashion Mart Configuration

Check that all Fashion Mart details are correct:

```python
from gurtoy_bot import config

print(f"Store Address: {config.BUSINESS_ADDRESS}")
print(f"Phone (Inquiry): {config.BUSINESS_PHONE_INQUIRY}")
print(f"Phone (Buy): {config.BUSINESS_PHONE_BUY}")
print(f"Email: {config.BUSINESS_EMAIL}")
print(f"Maps: {config.BUSINESS_MAPS}")
```

### 2. Knowledge Base Verification

Check knowledge chunks loaded correctly:

```bash
# Test knowledge search
python -c "
from knowledge_data import get_knowledge_chunks
chunks = get_knowledge_chunks()
print(f'✅ {len(chunks)} knowledge chunks loaded')
for chunk in chunks:
    print(f\"  - {chunk['chunk_id']}: {chunk['title']}\")
"
```

Expected chunks:
- company_overview: Fashion Mart Company Overview
- contact_information: Fashion Mart Contact Information
- product_categories: Fashion Mart Product Categories
- sizing_information: Size Guide and Fitting Information

### 3. Monitor Bot Status (GCP)

```bash
# Check supervisor status
sudo supervisorctl status gurtoy-bot

# Restart if needed
sudo supervisorctl restart gurtoy-bot

# Stop
sudo supervisorctl stop gurtoy-bot

# View logs
sudo tail -f /var/log/gurtoy-bot.out.log
```

### 4. Enable Optional Features

#### Payment Processing
- Fill in `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in .env
- Restart bot: `sudo supervisorctl restart gurtoy-bot`

#### Image Handling
- Already enabled, no additional config needed
- Images saved to `temp_images/`

#### Audio Handling
- Already enabled, no additional config needed
- Audio saved to `temp_audio/`

---

## 🔄 Updating Bot Code

### Local Development

```bash
# Make changes to .py files
# Restart bot
# Ctrl+C to stop, then:
python run_bot.py
```

### GCP Instance

```bash
# Update files from local machine
gcloud compute scp gurtoy_bot_polling.py INSTANCE_NAME:/opt/fashion-mart-bot/ --zone=us-central1-a

# Restart bot
gcloud compute ssh INSTANCE_NAME --zone=us-central1-a --command="sudo supervisorctl restart gurtoy-bot"
```

---

## 🚨 Troubleshooting

### Issue: "Telegram API Connection Failed"

**Solution**:
```bash
# Verify TELEGRAM_BOT_TOKEN in .env
# Test manually:
python -c "
import httpx
token = 'YOUR_TOKEN'
resp = httpx.get(f'https://api.telegram.org/bot{token}/getMe')
print(resp.json())
"
```

### Issue: "Supabase Connection Failed"

**Solution**:
```bash
# Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
# Verify database is accessible:
python setup_database.py
```

### Issue: "No Embeddings Generated"

**Solution**:
```bash
# Check GEMINI_API_KEY
# Verify it's active in Google AI Studio
# Re-run setup:
python setup_database.py
```

### Issue: Bot Not Responding

**GCP**: 
```bash
# Check logs
sudo tail -f /var/log/gurtoy-bot.out.log

# Check supervisor
sudo supervisorctl status gurtoy-bot

# Restart
sudo supervisorctl restart gurtoy-bot
```

**Local**:
- Check console output for errors
- Verify .env file is in root directory
- Ensure all dependencies installed: `pip install -r requirements.txt`

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Users                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Telegram Bot API                               │
│              (Polling Mode Recommended)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         gurtoy_bot_polling.py / run_bot.py                  │
│    (Telegram message handling & routing)                    │
└──────┬──────────────────────────────┬──────────┬────────────┘
       │                              │          │
       ▼                              ▼          ▼
  ┌─────────────┐          ┌──────────────────┐ ┌──────────────┐
  │ FashionMart │          │  Gemini AI       │ │  Knowledge   │
  │ AI System   │──────→   │  Vector Search   │─→ Base         │
  │             │          │  & Generation    │ │ (Fashion)    │
  └─────────────┘          └──────────────────┘ └──────────────┘
                                    │
                                    ▼
                        ┌──────────────────────┐
                        │  Supabase Database   │
                        │  - Users             │
                        │  - Sessions          │
                        │  - Knowledge (768d)  │
                        │  - Orders (optional) │
                        └──────────────────────┘
```

---

## 🎯 Next Steps After Deployment

1. **Test Bot Functionality**
   - Send messages to @YourBotName on Telegram
   - Verify Fashion Mart details are shown
   - Check product search works

2. **Enable Payment System** (optional)
   - Add Razorpay credentials
   - Test order flow

3. **Monitor Performance**
   - Check response times
   - Monitor API usage
   - Review user interactions

4. **Scale as Needed**
   - Increase GCP instance size if needed
   - Optimize database queries
   - Add caching layer

---

## 📞 Support

**Documentation**: See README.md in project root

**Contact**: 
- Phone: 9876151585 (Inquiry)
- Phone: 6283837649 (Sales)
- Email: fashionmart@gmail.com
- Maps: https://maps.app.goo.gl/koBoUFYEtE3mvdCC7

---

**Last Updated**: 2024 | Fashion Mart Phase 8 Complete Migration