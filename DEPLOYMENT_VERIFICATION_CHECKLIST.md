# 🔍 Fashion Mart Bot - Deployment Verification Checklist

**Status**: Ready for Fashion Mart Phase 8 Deployment ✅

---

## ✅ Pre-Deployment Checks

### Environment Configuration
- [ ] `.env` file exists in project root
- [ ] `GEMINI_API_KEY` is set and valid
- [ ] `TELEGRAM_BOT_TOKEN` is set and valid
- [ ] `SUPABASE_URL` is set
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is set
- [ ] `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are set (if using payments)
- [ ] `BUSINESS_ADDRESS` contains Fashion Mart Ludhiana address
- [ ] `BUSINESS_PHONE_INQUIRY` = "9876151585"
- [ ] `BUSINESS_PHONE_BUY` = "6283837649"
- [ ] `BUSINESS_EMAIL` = "fashionmart@gmail.com"

**Current Status**: ✅ ALL SET

```env
GEMINI_API_KEY=AIzaSyB1yfhAcsXvr5wM9u2oAigZTp0uWQRt27Q
TELEGRAM_BOT_TOKEN=7504641562:AAEm8-Au1d7rk9d8yJLeASnkQJuDQ6y6M7s
SUPABASE_URL=https://uejyfpzabmlrgkdayfrn.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
BUSINESS_ADDRESS=PLOT NO. B/31/1097/1, NEAR CHURCH...
BUSINESS_PHONE_INQUIRY=9876151585
BUSINESS_PHONE_BUY=6283837649
```

### File Inventory
- [ ] `gurtoy_bot_polling.py` exists (main polling bot)
- [ ] `gurtoy_bot.py` exists (webhook bot alternative)
- [ ] `run_bot.py` exists (launcher script)
- [ ] `requirements.txt` exists with all dependencies
- [ ] `setup_database.py` exists
- [ ] `knowledge_data.py` exists (Fashion Mart knowledge)
- [ ] `.env` exists with all credentials
- [ ] `supabase_schema.sql` exists

**Current Status**: ✅ ALL FILES PRESENT

---

## 🚀 Deployment Execution Checks

### Instance Creation (GCP)
- [ ] New instance created successfully
- [ ] Instance name follows pattern: `fashion-mart-bot-*`
- [ ] Machine type: `e2-medium` or larger
- [ ] Zone: `us-central1-a`
- [ ] Boot disk size: 20GB
- [ ] Instance is in "RUNNING" state

**Verify with**:
```bash
gcloud compute instances describe INSTANCE_NAME --zone=us-central1-a
```

### System Dependencies
- [ ] Python 3.9+ installed
- [ ] pip3 installed
- [ ] git installed
- [ ] supervisor installed
- [ ] build-essential installed

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="python3 --version && pip3 --version && sudo supervisorctl -h"
```

### Python Environment
- [ ] Virtual environment created at `/opt/fashion-mart-bot/venv`
- [ ] All requirements installed without errors
- [ ] No missing dependencies

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="source /opt/fashion-mart-bot/venv/bin/activate && pip list | grep -E 'google-generativeai|supabase|python-telegram-bot|fastapi'"
```

Expected output:
```
fastapi                    0.104.1
google-generativeai        0.8.0
python-telegram-bot        20.0
supabase                   2.0.0
```

### File Upload
- [ ] All Python files uploaded
- [ ] Configuration files (.env) uploaded
- [ ] Database schema file uploaded
- [ ] Invoice logo uploaded (if applicable)
- [ ] Directory structure created properly

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="ls -la /opt/fashion-mart-bot/ | head -20"
```

---

## 🧠 Database & Knowledge Base Checks

### Database Connection
- [ ] Supabase database accessible
- [ ] Table `gurtoy_knowledge` exists
- [ ] Vector extension enabled
- [ ] Connection test successful

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python -c \"from supabase import create_client; print('✅ Supabase OK')\""
```

### Knowledge Base Initialization
- [ ] Knowledge chunks loaded from `knowledge_data.py`
- [ ] 15+ fashion knowledge chunks loaded
- [ ] Embeddings generated with 768 dimensions
- [ ] Embeddings uploaded to Supabase
- [ ] Vector search operational

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python setup_database.py"
```

Expected output:
```
✅ Gemini API connection successful
✅ Supabase connection successful
✅ Loaded 15+ knowledge chunks
🧠 Generating embeddings...
✅ Embeddings generated successfully
✅ Database setup complete!
```

### Knowledge Chunks Verification
- [ ] `company_overview`: Fashion Mart company information
- [ ] `contact_information`: Address, phone, email, maps
- [ ] `product_categories`: Cardigans, crop tops, traditional wear, etc.
- [ ] `sizing_information`: Size guide S/M/L/XL
- [ ] `fashion_tips`: Style advice (if added)
- [ ] `return_policy`: Return & exchange policy
- [ ] `styling_guide`: Fashion recommendations

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python -c \"from knowledge_data import get_knowledge_chunks; chunks = get_knowledge_chunks(); print(f'✅ {len(chunks)} chunks loaded'); [print(f'  {c[\\\"chunk_id\\\"]}') for c in chunks[:7]]\""
```

---

## 🤖 Bot API Connection Checks

### Telegram API Connection
- [ ] Telegram bot token valid
- [ ] Bot can receive messages
- [ ] Bot can send messages
- [ ] Webhook mode ready (optional)

**Verify with**:
```bash
# Test telegram token
gcloud compute ssh INSTANCE_NAME --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python -c \"import httpx; token='7504641562:AAEm8-Au1d7rk9d8yJLeASnkQJuDQ6y6M7s'; resp = httpx.get(f'https://api.telegram.org/bot{token}/getMe'); print(resp.json())\""
```

### Gemini API Connection
- [ ] API key valid
- [ ] Embedding model accessible
- [ ] Chat model accessible
- [ ] Rate limits not exceeded

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="cd /opt/fashion-mart-bot && source venv/bin/activate && python -c \"import google.generativeai as genai; print('✅ Gemini OK')\""
```

---

## 🎯 Bot Functionality Checks

### Supervisor Configuration
- [ ] Supervisor service running
- [ ] `fashion-mart-bot` program configured
- [ ] Program set to autostart
- [ ] Program set to autorestart
- [ ] Log file configured at `/var/log/fashion-mart-bot.log`

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="sudo supervisorctl status fashion-mart-bot"
```

Expected output:
```
fashion-mart-bot         RUNNING   pid 1234, uptime 0:05:23
```

### Bot Startup
- [ ] Bot starts without errors
- [ ] No import errors
- [ ] Database connections established
- [ ] Polling mode active
- [ ] Ready to receive messages

**Verify with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="sudo tail -n 50 /var/log/fashion-mart-bot.log | grep -i 'started\|running\|listening\|polling'"
```

Expected logs should show:
```
[INFO] Polling bot started
[INFO] Connected to Supabase
[INFO] Gemini API ready
[INFO] Polling for messages...
```

### Basic Message Handling
- [ ] Bot receives messages successfully
- [ ] Bot processes messages
- [ ] Bot responds within 3 seconds

**Test**: Send "Hi" to bot in Telegram

---

## 🔍 Fashion Mart Configuration Checks

### Business Information
- [ ] Store address: "PLOT NO. B/31/1097/1, NEAR CHURCH, BACK SIDE POLICE COLONY NEAR ASIAN HOSPITAL BHAMIAN ROAD, Chandigarh Rd, Ludhiana, Punjab 141003"
- [ ] Inquiry phone: 9876151585
- [ ] Purchase phone: 6283837649
- [ ] Email: fashionmart@gmail.com
- [ ] Maps URL: https://maps.app.goo.gl/koBoUFYEtE3mvdCC7

**Test Message**: "What's your address?"

**Expected Response**: Shows Fashion Mart Ludhiana address

### Knowledge Base Content
- [ ] All product categories mentioned (Cardigans, Crop Tops, Traditional, etc.)
- [ ] All sizes mentioned (S, M, L, XL)
- [ ] Company overview reflects Fashion Mart
- [ ] No outdated toy/gurtoy references

**Test Message**: "What products do you sell?"

**Expected Response**: Fashion Mart product categories

---

## 🧪 Functional Testing

### Test 1: Basic Response
```
User:     "Hello"
Expected: Bot responds with greeting and Fashion Mart info
Status:   [ ] PASS / [ ] FAIL
```

### Test 2: Contact Information
```
User:     "What's your address?"
Expected: Shows Fashion Mart address, phone, email, maps
Status:   [ ] PASS / [ ] FAIL
```

### Test 3: Product Information
```
User:     "Show me cardigans"
Expected: Fashion Mart cardigan recommendations
Status:   [ ] PASS / [ ] FAIL
```

### Test 4: Size Information
```
User:     "What sizes do you have?"
Expected: Shows S/M/L/XL size guide
Status:   [ ] PASS / [ ] FAIL
```

### Test 5: Knowledge Search
```
User:     "Tell me about your clothing"
Expected: Fashion Mart fashion information
Status:   [ ] PASS / [ ] FAIL
```

### Test 6: Multilingual Support
```
User:     "नमस्ते" (Hindi)
Expected: Response in Hindi/Hinglish
Status:   [ ] PASS / [ ] FAIL
```

### Test 7: Order Flow (if payment enabled)
```
User:     "I want to order something"
Expected: Order collection flow starts
Status:   [ ] PASS / [ ] FAIL
```

### Test 8: Image Upload (optional)
```
User:     Uploads an image
Expected: Bot analyzes and responds about fashion item
Status:   [ ] PASS / [ ] FAIL
```

### Test 9: Error Handling
```
User:     Random gibberish
Expected: Bot handles gracefully, asks for clarification
Status:   [ ] PASS / [ ] FAIL
```

### Test 10: Long Conversation
```
User:     Multiple messages in sequence
Expected: Bot maintains context and conversation history
Status:   [ ] PASS / [ ] FAIL
```

---

## 📊 Performance Checks

### Response Time
- [ ] Average response time < 2 seconds
- [ ] No timeout errors
- [ ] API calls responsive

**Measure**:
- Send message and note timestamp
- Receive response and note timestamp
- Calculate difference

Expected: < 2 seconds for average message

### Resource Usage
- [ ] CPU usage < 40%
- [ ] Memory usage < 500MB
- [ ] Disk space available

**Check with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="top -bn1 | head -10"
gcloud compute ssh INSTANCE_NAME --command="free -h"
```

### Logging
- [ ] Logs written to `/var/log/fashion-mart-bot.log`
- [ ] Log rotation configured (maxbytes=10MB, backups=5)
- [ ] No excessive error logs

**Check with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="sudo tail -n 100 /var/log/fashion-mart-bot.log | grep -i error"
```

---

## 🔐 Security Checks

### Credentials Security
- [ ] No API keys logged to console
- [ ] No secrets in error messages
- [ ] `.env` file not exposed
- [ ] Supabase credentials protected

**Check with**:
```bash
gcloud compute ssh INSTANCE_NAME --command="sudo grep -i 'AIzaSy\|TELEGRAM_BOT' /var/log/fashion-mart-bot.log || echo 'Good - no secrets in logs'"
```

### Access Control
- [ ] Instance firewall configured
- [ ] Only necessary ports open
- [ ] SSH access restricted (if possible)

### Data Protection
- [ ] User data not exposed
- [ ] Conversation history properly stored
- [ ] No data leaks in responses

---

## 🚨 Issue Resolution Matrix

| Issue | Symptom | Solution |
|-------|---------|----------|
| Bot not responding | No messages in logs | Check Telegram token, restart bot |
| Database connection error | "Connection failed" in logs | Verify Supabase credentials, check database |
| No embeddings | "Embedding not found" error | Re-run `python setup_database.py` |
| Gemini API error | "API rate limit" in logs | Check API key, review quota |
| Fashion info not showing | Bot gives generic response | Verify knowledge_data.py loaded correctly |
| Supervisor not working | "Program not found" error | Check supervisor config, restart supervisorctl |

---

## 📋 Sign-Off Checklist

### Before Going Live
- [ ] All functionality tests PASS
- [ ] Performance metrics acceptable
- [ ] Security checks passed
- [ ] No errors in logs
- [ ] Knowledge base complete
- [ ] Business information correct
- [ ] Team approval received

### Post-Deployment Monitoring (First 24 Hours)
- [ ] Monitor logs for errors
- [ ] Check user message flow
- [ ] Verify all responses are relevant
- [ ] Monitor resource usage
- [ ] Track response times
- [ ] No crashes or restarts

### Ongoing Maintenance
- [ ] Weekly: Check logs for patterns
- [ ] Weekly: Verify bot still responding
- [ ] Monthly: Review performance metrics
- [ ] Monthly: Update knowledge base if needed
- [ ] Quarterly: Security audit

---

## 📞 Quick Commands Reference

```bash
# Connect to instance
gcloud compute ssh INSTANCE_NAME --zone=us-central1-a

# View bot status
sudo supervisorctl status fashion-mart-bot

# View live logs
sudo tail -f /var/log/fashion-mart-bot.log

# Restart bot
sudo supervisorctl restart fashion-mart-bot

# Stop bot
sudo supervisorctl stop fashion-mart-bot

# Start bot
sudo supervisorctl start fashion-mart-bot

# Check disk space
df -h

# Check memory
free -h

# Check running processes
ps aux | grep python

# Test Telegram API
curl https://api.telegram.org/botTOKEN/getMe

# Generate new embeddings
cd /opt/fashion-mart-bot && source venv/bin/activate && python setup_database.py
```

---

## ✨ Deployment Complete When:

✅ Instance is RUNNING
✅ Bot is RUNNING (supervisor status shows RUNNING)
✅ All 10 functional tests PASS
✅ Response time < 2 seconds
✅ No errors in logs
✅ Business info correct
✅ Knowledge base loaded (15+ chunks)
✅ Team approval received

---

**Last Updated**: 2024 | Fashion Mart Phase 8 Complete Migration
**Deployment Type**: Fresh GCP Instance
**Mode**: Polling (No Webhook)
**Niche**: Fashion Mart Women's Fashion