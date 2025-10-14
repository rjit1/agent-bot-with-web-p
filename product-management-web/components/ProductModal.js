import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Grid
} from '@mui/material'
import { useForm, Controller } from 'react-hook-form'
import axios from 'axios'
import ImageUpload from './ImageUploadSimple'
import SpecificationsInput from './SpecificationsInput'

export default function ProductModal({ open, onClose, onSave, product }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [images, setImages] = useState([])

  const { control, handleSubmit, reset, formState: { errors }, watch } = useForm({
    defaultValues: {
      product_id: '',
      title: '',
      category: '',
      description: '',
      specifications: '{}',
      price: '',
      discount_price: '',
      stock_status: 'in_stock',
      warranty: ''
    }
  })

  useEffect(() => {
    if (product) {
      reset({
        product_id: product.product_id || '',
        title: product.title || '',
        category: product.category || '',
        description: product.description || '',
        specifications: JSON.stringify(product.specifications || {}, null, 2),
        price: product.price || '',
        discount_price: product.discount_price || '',
        stock_status: product.stock_status || 'in_stock',
        warranty: product.warranty || ''
      })
      setImages(product.images || [])
    } else {
      reset({
        product_id: '',
        title: '',
        category: '',
        description: '',
        specifications: '{}',
        price: '',
        discount_price: '',
        stock_status: 'in_stock',
        warranty: ''
      })
      setImages([])
    }
  }, [product, reset])

  const onSubmit = async (data) => {
    setLoading(true)
    setError('')

    try {
      const token = localStorage.getItem('auth_token')
      
      // Parse specifications JSON
      let specifications = {}
      try {
        specifications = JSON.parse(data.specifications)
      } catch (e) {
        throw new Error('Invalid JSON format in specifications')
      }

      const productData = {
        ...data,
        specifications,
        price: parseFloat(data.price),
        discount_price: data.discount_price ? parseFloat(data.discount_price) : null,
        images
      }

      if (product) {
        // Update existing product
        await axios.put(`/api/products/${product.product_id}`, productData, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } else {
        // Create new product
        await axios.post('/api/products', productData, {
          headers: { Authorization: `Bearer ${token}` }
        })
      }

      onSave()
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save product')
      console.error('Save product error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleImageUpload = (newImages) => {
    setImages(prev => [...prev, ...newImages])
  }

  const handleRemoveImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {product ? 'Edit Product' : 'Add New Product'}
      </DialogTitle>
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Controller
                name="product_id"
                control={control}
                rules={{ required: 'Product ID is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Product ID"
                    fullWidth
                    error={!!errors.product_id}
                    helperText={errors.product_id?.message}
                    disabled={!!product} // Don't allow editing ID for existing products
                  />
                )}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Controller
                name="category"
                control={control}
                rules={{ required: 'Category is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Category"
                    fullWidth
                    error={!!errors.category}
                    helperText={errors.category?.message || 'Enter product category (e.g., Electronics, Toys, Clothing)'}
                    placeholder="e.g., Electronics, Toys & Games, Clothing"
                  />
                )}
              />
            </Grid>

            <Grid item xs={12}>
              <Controller
                name="title"
                control={control}
                rules={{ required: 'Title is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Product Title"
                    fullWidth
                    error={!!errors.title}
                    helperText={errors.title?.message}
                  />
                )}
              />
            </Grid>

            <Grid item xs={12}>
              <Controller
                name="description"
                control={control}
                rules={{ required: 'Description is required' }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Description"
                    fullWidth
                    multiline
                    rows={3}
                    error={!!errors.description}
                    helperText={errors.description?.message}
                  />
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Controller
                name="price"
                control={control}
                rules={{ 
                  required: 'Price is required',
                  pattern: {
                    value: /^\d+(\.\d{1,2})?$/,
                    message: 'Invalid price format'
                  }
                }}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Price (₹)"
                    type="number"
                    fullWidth
                    error={!!errors.price}
                    helperText={errors.price?.message}
                  />
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Controller
                name="discount_price"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Discount Price (₹)"
                    type="number"
                    fullWidth
                    error={!!errors.discount_price}
                    helperText={errors.discount_price?.message}
                  />
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Controller
                name="stock_status"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth>
                    <InputLabel>Stock Status</InputLabel>
                    <Select {...field} label="Stock Status">
                      <MenuItem value="in_stock">In Stock</MenuItem>
                      <MenuItem value="out_of_stock">Out of Stock</MenuItem>
                      <MenuItem value="pre_order">Pre Order</MenuItem>
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Controller
                name="warranty"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Warranty"
                    fullWidth
                    placeholder="e.g., 1 Year Warranty"
                  />
                )}
              />
            </Grid>

            <Grid item xs={12}>
              <Controller
                name="specifications"
                control={control}
                render={({ field }) => (
                  <SpecificationsInput
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.specifications?.message}
                    helperText="Add key-value pairs for product specifications (e.g., Battery: 8 hours, Weight: 200g)"
                  />
                )}
              />
            </Grid>

            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Product Images
              </Typography>
              <ImageUpload
                onUpload={handleImageUpload}
                images={images}
                onRemove={handleRemoveImage}
              />
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button 
            type="submit" 
            variant="contained" 
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Save Product'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
