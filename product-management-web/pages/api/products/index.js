import { NextApiRequest, NextApiResponse } from 'next'
import { getSupabaseAdmin, TABLES } from '../../../lib/supabase'
import { verifyToken, getAuthToken } from '../../../lib/auth'

export default async function handler(req, res) {
  // Verify authentication
  const token = getAuthToken(req)
  const payload = await verifyToken(token)
  
  if (!payload || !payload.authenticated) {
    return res.status(401).json({ error: 'Unauthorized' })
  }

  try {
    switch (req.method) {
      case 'GET':
        return await getProducts(req, res)
      case 'POST':
        return await createProduct(req, res)
      default:
        return res.status(405).json({ error: 'Method not allowed' })
    }
  } catch (error) {
    console.error('Products API error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

async function getProducts(req, res) {
  const { search, category, page = 1, limit = 20 } = req.query
  
  try {
    let query = getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .select('*')
      .order('created_at', { ascending: false })

    // Apply search filter
    if (search) {
      query = query.or(`product_id.ilike.%${search}%,title.ilike.%${search}%`)
    }

    // Apply category filter
    if (category) {
      query = query.eq('category', category)
    }

    // Apply pagination
    const from = (page - 1) * limit
    const to = from + limit - 1
    query = query.range(from, to)

    const { data, error, count } = await query

    if (error) {
      throw error
    }

    res.status(200).json({
      products: data || [],
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: count || 0,
        pages: Math.ceil((count || 0) / limit)
      }
    })

  } catch (error) {
    console.error('Get products error:', error)
    res.status(500).json({ error: 'Failed to fetch products' })
  }
}

async function createProduct(req, res) {
  const { 
    product_id, 
    title, 
    category, 
    description, 
    specifications, 
    images,
    price, 
    discount_price, 
    stock_status, 
    warranty 
  } = req.body

  // Validate required fields
  if (!product_id || !title || !category || !description || !price) {
    return res.status(400).json({ 
      error: 'Missing required fields: product_id, title, category, description, price' 
    })
  }

  try {
    const productData = {
      product_id,
      title,
      category,
      description,
      specifications: specifications || {},
      images: images || [], // Use uploaded images from request
      price: parseFloat(price),
      discount_price: discount_price ? parseFloat(discount_price) : null,
      stock_status: stock_status || 'in_stock',
      warranty: warranty || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    const { data, error } = await getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .insert([productData])
      .select()
      .single()

    if (error) {
      if (error.code === '23505') {
        return res.status(400).json({ error: 'Product ID already exists' })
      }
      throw error
    }

    res.status(201).json({ 
      success: true, 
      product: data,
      message: 'Product created successfully'
    })

  } catch (error) {
    console.error('Create product error:', error)
    res.status(500).json({ error: 'Failed to create product' })
  }
}
