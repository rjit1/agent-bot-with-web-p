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

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // Get unique categories from products
    const { data, error } = await getSupabaseAdmin()
      .from(TABLES.PRODUCTS)
      .select('category')
      .not('category', 'is', null)

    if (error) {
      throw error
    }

    // Extract unique categories
    const categories = [...new Set(data.map(item => item.category))]
      .filter(Boolean)
      .sort()

    res.status(200).json({ categories })

  } catch (error) {
    console.error('Get categories error:', error)
    res.status(500).json({ error: 'Failed to fetch categories' })
  }
}
