import { NextApiRequest, NextApiResponse } from 'next'
import { getSupabaseAdmin, STORAGE_BUCKET } from '../../../lib/supabase'
import { verifyToken, getAuthToken } from '../../../lib/auth'

export default async function handler(req, res) {
  // Verify authentication
  const token = getAuthToken(req)
  const payload = await verifyToken(token)
  
  if (!payload || !payload.authenticated) {
    return res.status(401).json({ error: 'Unauthorized' })
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { productId, imageUrl, imageName } = req.body

    if (!productId || !imageUrl) {
      return res.status(400).json({ error: 'Product ID and image URL are required' })
    }

    // Get current product
    const { data: product, error: fetchError } = await getSupabaseAdmin()
      .from('products')
      .select('images')
      .eq('product_id', productId)
      .single()

    if (fetchError) {
      return res.status(404).json({ error: 'Product not found' })
    }

    // Update images array
    const currentImages = product.images || []
    const newImages = [...currentImages, {
      url: imageUrl,
      name: imageName || 'product-image',
      uploaded_at: new Date().toISOString()
    }]

    const { data, error } = await getSupabaseAdmin()
      .from('products')
      .update({ 
        images: newImages,
        updated_at: new Date().toISOString()
      })
      .eq('product_id', productId)
      .select()
      .single()

    if (error) {
      throw error
    }

    res.status(200).json({ 
      success: true, 
      product: data,
      message: 'Image uploaded successfully'
    })

  } catch (error) {
    console.error('Upload image error:', error)
    res.status(500).json({ error: 'Failed to upload image' })
  }
}
