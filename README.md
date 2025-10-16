# Fashion Mart Telegram Bot - Phase 8: Complete Migration

A multilingual, context-aware AI assistant for Fashion Mart women's fashion store built with Gemini 2.5 Flash, Supabase, and Telegram Bot API.

## 🌟 Features

### Phase 8 Capabilities
- **Multilingual Support**: English, Hindi, and Hinglish responses
- **Context-Aware Conversations**: Remembers user preferences and conversation history
- **Fashion Knowledge Base**: Vector search through fashion store information
- **Function Calling**: Dynamic routing to tools and APIs
- **Sentiment Analysis**: Tracks conversation sentiment for analytics
- **Human Escalation**: Seamless handoff to human agents when needed
- **Safety & Compliance**: Content filtering and PII protection
- **Fashion Image Analysis**: AI-powered fashion item recognition and styling advice
- **Size Recommendations**: AI-powered size estimation and recommendations
- **Style Coordination**: Color and style coordination suggestions
- **Occasion-Based Recommendations**: Event-appropriate fashion suggestions

### Key Functions
- Fashion item information and recommendations
- Store location and contact details
- Return policy and customer service
- Order assistance and support
- Size recommendations and fit guidance
- Style advice and color coordination
- Occasion-based fashion suggestions
- Cultural sensitivity for Indian customers

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram      │    │   FastAPI        │    │   Supabase      │
│   Bot API       │◄──►│   Webhook        │◄──►│   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Gemini 2.5     │
                       │   Flash + Tools  │
                       └──────────────────┘
```

## 📋 Prerequisites

- Python 3.9+
- Supabase account and project
- Google AI Studio API key (Gemini)
- Telegram Bot Token
- PostgreSQL with vector extension (provided by Supabase)

## ⚠️ Important: Vector Dimensions

**Before setup**, please read [`VECTOR_DIMENSIONS_GUIDE.md`](./VECTOR_DIMENSIONS_GUIDE.md) for important information about Supabase's 2,000-dimension limit and our 1536-dimension solution.

## 🚀 Quick Start

### ⚡ Super Quick Start (Polling Mode - Recommended)

**No webhook setup required! Perfect for local development.**

```bash
# 1. Setup database (one-time)
python setup_database.py

# 2. Run the bot
python run_bot.py
```

That's it! Your bot is now running. See [`QUICKSTART.md`](./QUICKSTART.md) for details.

### 📚 Detailed Setup

### 1. Clone and Setup

```bash
git clone <repository-url>
cd gurtoy-telegram-bot
pip install -r requirements.txt
```

### 2. Environment Configuration

Your `.env` file is already configured! Required variables:
```env
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

**Note**: `TELEGRAM_WEBHOOK_URL` and `TELEGRAM_WEBHOOK_SECRET` are now **optional** (only needed for webhook mode).

### 3. Database Setup

Run the SQL schema in your Supabase SQL editor:
```bash
# Copy contents of supabase_schema.sql to Supabase SQL editor and execute
```

Prepare and load knowledge data:
```bash
python setup_database.py
```

### 4. Run the Bot

**Option A: Polling Mode (Recommended for Development)**
```bash
python run_bot.py
```
- ✅ No webhook setup required
- ✅ No ngrok needed
- ✅ Works immediately
- ✅ Perfect for local testing

**Option B: Webhook Mode (For Production)**
```bash
# Terminal 1: Start the bot server
python gurtoy_bot.py

# Terminal 2: Setup webhook with ngrok
python deploy_bot.py
```
- Requires public URL
- See [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) for details

### 5. Test the Bot

```bash
python test_bot.py
```

The bot will start on `http://localhost:8000`

## 🔄 Bot Operation Modes

The bot supports two modes of operation:

### Polling Mode (Recommended for Development)
- **File**: `gurtoy_bot_polling.py`
- **Launcher**: `run_bot.py`
- **How it works**: Bot polls Telegram API for new messages
- **Advantages**:
  - ✅ No webhook setup required
  - ✅ No public URL needed
  - ✅ No ngrok required
  - ✅ Works on any machine instantly
  - ✅ Perfect for local development
- **Disadvantages**:
  - ⚠️ ~1-2 second message delay
  - ⚠️ Slightly higher resource usage
- **Use when**: Developing, testing, or no public server available

### Webhook Mode (Recommended for Production)
- **File**: `gurtoy_bot.py`
- **Deployment**: `deploy_bot.py`
- **How it works**: Telegram sends messages to your webhook URL
- **Advantages**:
  - ✅ Instant message delivery
  - ✅ Lower resource usage
  - ✅ Better for high traffic
  - ✅ Production-ready
- **Disadvantages**:
  - ⚠️ Requires public URL
  - ⚠️ Requires webhook setup
  - ⚠️ More complex deployment
- **Use when**: Deploying to production with proper hosting

**See [`POLLING_MODE_GUIDE.md`](./POLLING_MODE_GUIDE.md) for detailed comparison.**

## 📊 Database Schema

### Core Tables

- **`gurtoy_knowledge`**: Company knowledge with vector embeddings
- **`users`**: Telegram user profiles and preferences
- **`sessions`**: Active conversation sessions
- **`conversation_logs`**: Complete conversation history
- **`sentiment_tags`**: Sentiment analysis results
- **`handoff_requests`**: Human escalation requests

### Key Functions

- **`search_knowledge()`**: Vector similarity search
- **`get_user_context()`**: Retrieve user session data
- **`update_user_activity()`**: Track user engagement

## 🔧 Configuration

### AI Model Settings
```env
DEFAULT_TEMPERATURE=0.7
SIMILARITY_THRESHOLD=0.7
MAX_SEARCH_RESULTS=5
CHAT_MODEL=gemini-2.5-flash-latest
EMBEDDING_MODEL=models/embedding-001
```

### Business Settings
```env
BUSINESS_PHONE=8300000086
BUSINESS_EMAIL=thegurtoy@gmail.com
BUSINESS_WHATSAPP=8300000086
```

## 🧪 Testing

### Run All Tests
```bash
python test_bot.py
```

### Interactive Testing
```bash
python test_bot.py
# Choose 'y' for interactive mode
```

### Test Specific Components
```python
# Test knowledge search
await ai.search_knowledge("toys for kids", "products")

# Test contact info
contact = ai.get_contact_info("all")

# Test AI response
response = await ai.generate_response("What toys do you sell?")
```

## 🚀 Deployment

### Local Development
```bash
python gurtoy_bot.py
```

### Production Deployment

1. **Set up webhook URL** in your production environment
2. **Configure environment variables** for production
3. **Set up monitoring** and logging
4. **Configure rate limiting** and security

Example with Docker:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "gurtoy_bot.py"]
```

### Webhook Setup

Set your webhook URL with Telegram:
```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/telegram/webhook"}'
```

## 📈 Monitoring

### Health Checks
- `GET /` - Basic health check
- `GET /health` - Detailed service status

### Logging
The bot uses structured logging with different levels:
- `INFO`: Normal operations
- `ERROR`: Error conditions
- `DEBUG`: Detailed debugging (development only)

### Analytics
Conversation data is stored for analytics:
- Response times
- User engagement patterns
- Function call frequency
- Sentiment trends

## 🔒 Security

### Data Protection
- Row Level Security (RLS) on all user tables
- Environment variable protection
- Input validation and sanitization
- Rate limiting on API endpoints

### Privacy
- PII detection and redaction
- User data encryption
- Conversation data retention policies
- GDPR compliance considerations

## 🛠️ Development

### Project Structure
```
gurtoy-telegram-bot/
├── gurtoy_bot.py              # Main bot application
├── knowledge_preparation.py   # Knowledge data preparation
├── setup_database.py         # Database setup script
├── test_bot.py               # Testing utilities
├── supabase_schema.sql       # Database schema
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md               # This file
```

### Adding New Features

1. **Extend Knowledge Base**: Add new chunks in `knowledge_preparation.py`
2. **Add Functions**: Create new tools in `FashionMartAI` class
3. **Modify Responses**: Update system instructions and prompts
4. **Add Analytics**: Extend conversation logging

### Code Style
- Use `black` for code formatting
- Follow PEP 8 guidelines
- Add type hints for all functions
- Document all public methods

## 🐛 Troubleshooting

### Common Issues

1. **"No embedding found"**
   - Check Gemini API key
   - Verify internet connection
   - Check API quotas

2. **"Supabase connection failed"**
   - Verify Supabase URL and keys
   - Check database permissions
   - Ensure vector extension is enabled

3. **"Telegram webhook not working"**
   - Verify bot token
   - Check webhook URL accessibility
   - Review Telegram API logs

### Debug Mode
Set `DEBUG=true` in `.env` for detailed logging:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📞 Support

For technical support or questions:
- **Email**: thegurtoy@gmail.com
- **Phone**: 8300000086
- **WhatsApp**: wa.me/8300000086

## 🗺️ Roadmap

### Phase 2: Product Discovery (Planned)
- Multimodal product cards
- Advanced recommendation engine
- Inventory integration
- Shopping cart functionality

### Phase 3: Payments (Planned)
- Razorpay integration
- Order management
- Invoice generation
- Payment tracking

### Phase 4: Vision Features (Planned)
- Image-based product search
- Visual product matching
- Mixed-modal conversations
- AR try-before-buy

## 📄 License

This project is proprietary software for Fashion Mart women's fashion store.

## 🙏 Acknowledgments

- Google Gemini AI for advanced language capabilities
- Supabase for database and backend services
- Telegram for bot platform
- FastAPI for web framework