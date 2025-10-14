import React, { useState, useCallback } from 'react'
import {
  Box,
  Button,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  IconButton,
  Alert,
  CircularProgress
} from '@mui/material'
import { Delete as DeleteIcon, CloudUpload as UploadIcon } from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'
import { supabase, STORAGE_BUCKET } from '../lib/supabase'
import axios from 'axios'

export default function ImageUpload({ onUpload, images = [], onRemove }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback(async (acceptedFiles) => {
    setUploading(true)
    setError('')

    try {
      const uploadPromises = acceptedFiles.map(async (file) => {
        // Create FormData for server-side upload
        const formData = new FormData()
        formData.append('file', file)

        // Upload via server-side API
        const token = localStorage.getItem('auth_token')
        const response = await axios.post('/api/upload/simple-upload', formData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        })

        if (!response.data.success) {
          throw new Error(response.data.error || 'Upload failed')
        }

        return {
          url: response.data.imageUrl,
          name: response.data.fileName,
          path: response.data.filePath,
          uploaded_at: new Date().toISOString()
        }
      })

      const uploadedImages = await Promise.all(uploadPromises)
      onUpload(uploadedImages)
    } catch (err) {
      setError('Failed to upload images: ' + err.message)
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.gif', '.webp']
    },
    maxSize: 5 * 1024 * 1024, // 5MB
    multiple: true
  })

  const handleRemoveImage = async (index, image) => {
    try {
      // Remove from Supabase Storage using the public client
      if (image.path) {
        const { error } = await supabase.storage
          .from(STORAGE_BUCKET)
          .remove([image.path])
        
        if (error) {
          console.error('Storage removal error:', error)
        }
      }
      
      onRemove(index)
    } catch (err) {
      console.error('Remove image error:', err)
      // Still remove from UI even if storage deletion fails
      onRemove(index)
    }
  }

  return (
    <Box>
      {/* Upload Area */}
      <Box
        {...getRootProps()}
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          borderRadius: 2,
          p: 3,
          textAlign: 'center',
          cursor: 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover'
          }
        }}
      >
        <input {...getInputProps()} />
        <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
        <Typography variant="h6" gutterBottom>
          {isDragActive ? 'Drop images here' : 'Drag & drop images here'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          or click to select files
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Supports: JPEG, PNG, GIF, WebP (Max 5MB each)
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {/* Upload Progress */}
      {uploading && (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
          <CircularProgress size={20} sx={{ mr: 1 }} />
          <Typography variant="body2">Uploading images...</Typography>
        </Box>
      )}

      {/* Image Preview Grid */}
      {images.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Uploaded Images ({images.length})
          </Typography>
          <Grid container spacing={2}>
            {images.map((image, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card>
                  <CardMedia
                    component="img"
                    height="140"
                    image={image.url}
                    alt={image.name}
                    sx={{ objectFit: 'cover' }}
                  />
                  <CardContent sx={{ p: 1 }}>
                    <Typography variant="caption" noWrap>
                      {image.name}
                    </Typography>
                  </CardContent>
                  <CardActions sx={{ p: 1, justifyContent: 'center' }}>
                    <IconButton
                      color="error"
                      size="small"
                      onClick={() => handleRemoveImage(index, image)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  )
}
