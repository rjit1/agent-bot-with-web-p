# 🛍️ Product Management Web Application

A modern, mobile-friendly web application for managing products with password authentication and Supabase integration.

## 🌟 Features

- **Password Authentication** - Simple password-based access (121233)
- **Product CRUD Operations** - Create, Read, Update, Delete products
- **Image Upload** - Upload product images to Supabase Storage
- **Search & Filter** - Search by Product ID or Title, filter by category
- **Mobile Responsive** - Optimized for mobile devices
- **Real-time Updates** - Instant product list updates
- **Modern UI** - Material-UI components with professional design

## 🚀 Quick Start

### 1. Environment Setup

Copy the environment file and configure your Supabase credentials:

```bash
cp env.example .env.local
```

Update `.env.local` with your Supabase details:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
ADMIN_PASSWORD=121233
JWT_SECRET=your_jwt_secret_here
NEXT_PUBLIC_APP_NAME=Gurtoy Product Management
NEXT_PUBLIC_CONTACT_TELEGRAM=@Sarvesh_101
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Setup Supabase Storage

Create a storage bucket named `product-images` in your Supabase dashboard:

1. Go to Supabase Dashboard → Storage
2. Create new bucket: `product-images`
3. Set it to public
4. Configure RLS policies if needed

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📱 Mobile Features

- **Touch-friendly Interface** - Optimized for mobile devices
- **Responsive Grid** - Adapts to different screen sizes
- **Mobile Navigation** - Easy-to-use mobile controls
- **Image Upload** - Drag & drop works on mobile
- **Fast Loading** - Optimized for mobile performance

## 🔐 Authentication

- **Password**: `121233`
- **Session**: 24-hour JWT token
- **Security**: Password-protected access
- **Contact**: Wrong password? Message @Sarvesh_101 on Telegram

## 🗄️ Database Schema

The application uses the existing `products` table with these fields:

- `product_id` - Unique product identifier
- `title` - Product name
- `category` - Product category
- `description` - Product description
- `specifications` - JSON specifications
- `price` - Product price
- `discount_price` - Discounted price (optional)
- `stock_status` - Stock availability
- `warranty` - Warranty information
- `images` - Array of image URLs
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## 🚀 Deployment

### Option 1: Vercel (Recommended)

1. Push code to GitHub
2. Connect to Vercel
3. Add environment variables
4. Deploy automatically

### Option 2: Manual Deployment

```bash
# Build the application
npm run build

# Start production server
npm start
```

### Option 3: Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🔧 API Endpoints

- `POST /api/auth/login` - Authenticate with password
- `GET /api/products` - List products with search/filter
- `POST /api/products` - Create new product
- `GET /api/products/[id]` - Get single product
- `PUT /api/products/[id]` - Update product
- `DELETE /api/products/[id]` - Delete product
- `POST /api/products/upload-image` - Upload product image
- `GET /api/categories` - Get all categories

## 📊 Features Overview

### Product Management
- ✅ Add new products
- ✅ Edit existing products
- ✅ Delete products
- ✅ Search by ID or title
- ✅ Filter by category
- ✅ Image upload and management

### User Experience
- ✅ Password authentication
- ✅ Mobile-responsive design
- ✅ Real-time updates
- ✅ Error handling
- ✅ Loading states
- ✅ Professional UI

### Technical Features
- ✅ Next.js API routes
- ✅ Supabase integration
- ✅ JWT authentication
- ✅ Image storage
- ✅ Responsive design
- ✅ TypeScript support

## 🛠️ Development

### Project Structure

```
product-management-web/
├── pages/
│   ├── api/           # API routes
│   ├── login.js       # Login page
│   └── index.js       # Main dashboard
├── components/        # React components
├── lib/              # Utilities
├── styles/           # Global styles
└── public/           # Static assets
```

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## 🔒 Security

- Password-based authentication
- JWT token validation
- Supabase RLS policies
- Input validation
- XSS protection
- CSRF protection

## 📞 Support

- **Password Issues**: Contact @Sarvesh_101 on Telegram
- **Technical Support**: Check console logs for errors
- **Feature Requests**: Create GitHub issue

## 📄 License

This project is proprietary software for Gurtoy Product Management.

---

**Built with ❤️ using Next.js, Material-UI, and Supabase**
