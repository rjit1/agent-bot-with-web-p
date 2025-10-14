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
    const formData = await req.formData()
    const file = formData.get('file')
    const productId = formData.get('productId')

    if (!file || !productId) {
      return res.status(400).json({ error: 'File and Product ID are required' })
    }

    // Generate unique filename
    const fileExt = file.name.split('.').pop()
    const fileName = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExt}`
    const filePath = `products/${fileName}`

    // Upload to Supabase Storage using admin client
    const supabaseAdmin = getSupabaseAdmin()
    const { data: uploadData, error: uploadError } = await supabaseAdmin.storage
      .from(STORAGE_BUCKET)
      .upload(filePath, file)

    if (uploadError) {
      console.error('Upload error:', uploadError)
      return res.status(500).json({ error: 'Failed to upload image: ' + uploadError.message })
    }

    // Get public URL
    const { data: { publicUrl } } = supabaseAdmin.storage
      .from(STORAGE_BUCKET)
      .getPublicUrl(filePath)

    // Update product with new image
    const { data: product, error: fetchError } = await supabaseAdmin
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
      url: publicUrl,
      name: file.name,
      path: filePath,
      uploaded_at: new Date().toISOString()
    }]

    const { data, error } = await supabaseAdmin
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
      imageUrl: publicUrl,
      message: 'Image uploaded successfully'
    })

  } catch (error) {
    console.error('Upload image error:', error)
    res.status(500).json({ error: 'Failed to upload image' })
  }
}

// Disable body parsing for file uploads
export const config = {
  api: {
    bodyParser: false,
  },
}
