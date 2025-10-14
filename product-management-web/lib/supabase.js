import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

// Client for public operations (client-side)
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Admin client for server-side operations only
export const getSupabaseAdmin = () => {
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!supabaseServiceKey) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY is required for server-side operations')
  }
  return createClient(supabaseUrl, supabaseServiceKey)
}

// Storage bucket name
export const STORAGE_BUCKET = 'product-images'

// Database table names
export const TABLES = {
  PRODUCTS: 'products',
  CATEGORIES: 'categories'
}
