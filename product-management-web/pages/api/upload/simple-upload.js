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
    // Parse multipart form data manually
    const boundary = req.headers['content-type']?.split('boundary=')[1]
    if (!boundary) {
      return res.status(400).json({ error: 'No boundary found in content-type' })
    }

    const chunks = []
    req.on('data', chunk => chunks.push(chunk))
    
    await new Promise((resolve, reject) => {
      req.on('end', resolve)
      req.on('error', reject)
    })

    const buffer = Buffer.concat(chunks)
    const body = buffer.toString('binary')
    
    // Parse the multipart data
    const parts = body.split(`--${boundary}`)
    let file = null
    let fileName = ''
    let fileType = ''

    for (const part of parts) {
      if (part.includes('Content-Disposition: form-data')) {
        const lines = part.split('\r\n')
        const disposition = lines.find(line => line.startsWith('Content-Disposition:'))
        
        if (disposition && disposition.includes('name="file"')) {
          const filenameMatch = disposition.match(/filename="([^"]+)"/)
          if (filenameMatch) {
            fileName = filenameMatch[1]
            fileType = lines.find(line => line.startsWith('Content-Type:'))?.split(':')[1]?.trim() || 'image/jpeg'
            
            // Extract file content (skip headers)
            const contentStart = part.indexOf('\r\n\r\n') + 4
            const contentEnd = part.lastIndexOf('\r\n')
            const fileContent = part.substring(contentStart, contentEnd)
            
            file = Buffer.from(fileContent, 'binary')
            break
          }
        }
      }
    }

    if (!file || !fileName) {
      return res.status(400).json({ error: 'No file found in request' })
    }

    // Generate unique filename
    const fileExt = fileName.split('.').pop()
    const uniqueFileName = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExt}`
    const filePath = `products/${uniqueFileName}`

    // Upload to Supabase Storage using admin client
    const supabaseAdmin = getSupabaseAdmin()
    const { data: uploadData, error: uploadError } = await supabaseAdmin.storage
      .from(STORAGE_BUCKET)
      .upload(filePath, file, {
        contentType: fileType,
        upsert: false
      })

    if (uploadError) {
      console.error('Upload error:', uploadError)
      return res.status(500).json({ error: 'Failed to upload image: ' + uploadError.message })
    }

    // Get public URL
    const { data: { publicUrl } } = supabaseAdmin.storage
      .from(STORAGE_BUCKET)
      .getPublicUrl(filePath)

    res.status(200).json({ 
      success: true, 
      imageUrl: publicUrl,
      fileName: fileName,
      filePath: filePath,
      message: 'Image uploaded successfully'
    })

  } catch (error) {
    console.error('Upload image error:', error)
    res.status(500).json({ error: 'Failed to upload image: ' + error.message })
  }
}

// Disable body parsing for file uploads
export const config = {
  api: {
    bodyParser: false,
  },
}
