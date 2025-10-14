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

  const { id } = req.query

  if (!id) {
    return res.status(400).json({ error: 'Product ID is required' })
  }

  try {
    switch (req.method) {
      case 'GET':
        return await getProduct(req, res, id)
      case 'PUT':
        return await updateProduct(req, res, id)
      case 'DELETE':
        return await deleteProduct(req, res, id)
      default:
        return res.status(405).json({ error: 'Method not allowed' })
    }
  } catch (error) {
    console.error('Product API error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

async function getProduct(req, res, id) {
  try {
    const { data, error } = await getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .select('*')
      .eq('product_id', id)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return res.status(404).json({ error: 'Product not found' })
      }
      throw error
    }

    res.status(200).json({ product: data })

  } catch (error) {
    console.error('Get product error:', error)
    res.status(500).json({ error: 'Failed to fetch product' })
  }
}

async function updateProduct(req, res, id) {
  const { 
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

  try {
    const updateData = {
      updated_at: new Date().toISOString()
    }

    // Only update provided fields
    if (title !== undefined) updateData.title = title
    if (category !== undefined) updateData.category = category
    if (description !== undefined) updateData.description = description
    if (specifications !== undefined) updateData.specifications = specifications
    if (images !== undefined) updateData.images = images // Handle images update
    if (price !== undefined) updateData.price = parseFloat(price)
    if (discount_price !== undefined) updateData.discount_price = discount_price ? parseFloat(discount_price) : null
    if (stock_status !== undefined) updateData.stock_status = stock_status
    if (warranty !== undefined) updateData.warranty = warranty

    const { data, error } = await getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .update(updateData)
      .eq('product_id', id)
      .select()
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return res.status(404).json({ error: 'Product not found' })
      }
      throw error
    }

    res.status(200).json({ 
      success: true, 
      product: data,
      message: 'Product updated successfully'
    })

  } catch (error) {
    console.error('Update product error:', error)
    res.status(500).json({ error: 'Failed to update product' })
  }
}

async function deleteProduct(req, res, id) {
  try {
    const { error } = await getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .delete()
      .eq('product_id', id)

    if (error) {
      throw error
    }

    res.status(200).json({ 
      success: true,
      message: 'Product deleted successfully'
    })

  } catch (error) {
    console.error('Delete product error:', error)
    res.status(500).json({ error: 'Failed to delete product' })
  }
}
