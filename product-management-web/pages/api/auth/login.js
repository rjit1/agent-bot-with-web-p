import { NextApiRequest, NextApiResponse } from 'next'
import { verifyPassword, createToken } from '../../../lib/auth'

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { password } = req.body

    if (!password) {
      return res.status(400).json({ error: 'Password is required' })
    }

    const isValid = await verifyPassword(password)

    if (!isValid) {
      return res.status(401).json({ 
        error: 'Invalid password',
        message: 'Wrong password. Contact developer, message on telegram @Sarvesh_101'
      })
    }

    // Create JWT token
    const token = await createToken({ 
      authenticated: true, 
      timestamp: Date.now() 
    })

    res.status(200).json({ 
      success: true, 
      token,
      message: 'Login successful'
    })

  } catch (error) {
    console.error('Login error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}
