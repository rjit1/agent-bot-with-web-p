import React, { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  TextField,
  InputAdornment,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Fab,
  Paper
} from '@mui/material'
import {
  Search as SearchIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Image as ImageIcon
} from '@mui/icons-material'
import { useRouter } from 'next/router'
import axios from 'axios'
import ProductModal from '../components/ProductModal'
import ImageUpload from '../components/ImageUpload'

export default function Home() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [categories, setCategories] = useState([])
  const [openModal, setOpenModal] = useState(false)
  const [editingProduct, setEditingProduct] = useState(null)
  const [error, setError] = useState('')
  const router = useRouter()

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('auth_token')
    if (!token) {
      router.push('/login')
      return
    }

    fetchProducts()
    fetchCategories()
  }, [router])

  const fetchProducts = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const params = new URLSearchParams()
      
      if (searchTerm) params.append('search', searchTerm)
      if (selectedCategory) params.append('category', selectedCategory)

      const response = await axios.get(`/api/products?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      setProducts(response.data.products || [])
    } catch (err) {
      setError('Failed to fetch products')
      console.error('Fetch products error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await axios.get('/api/categories', {
        headers: { Authorization: `Bearer ${token}` }
      })

      setCategories(response.data.categories || [])
    } catch (err) {
      console.error('Fetch categories error:', err)
    }
  }

  const handleSearch = () => {
    setLoading(true)
    fetchProducts()
  }

  const handleAddProduct = () => {
    setEditingProduct(null)
    setOpenModal(true)
  }

  const handleEditProduct = (product) => {
    setEditingProduct(product)
    setOpenModal(true)
  }

  const handleDeleteProduct = async (productId) => {
    if (!confirm('Are you sure you want to delete this product?')) {
      return
    }

    try {
      const token = localStorage.getItem('auth_token')
      await axios.delete(`/api/products/${productId}`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      fetchProducts() // Refresh the list
    } catch (err) {
      setError('Failed to delete product')
      console.error('Delete product error:', err)
    }
  }

  const handleModalClose = () => {
    setOpenModal(false)
    setEditingProduct(null)
  }

  const handleProductSaved = () => {
    fetchProducts()
    handleModalClose()
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    router.push('/login')
  }

  if (loading && products.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Product Management
        </Typography>
        <Button variant="outlined" onClick={handleLogout}>
          Logout
        </Button>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              placeholder="Search by Product ID or Title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                label="Category"
              >
                <MenuItem value="">All Categories</MenuItem>
                {categories.map((category) => (
                  <MenuItem key={category} value={category}>
                    {category}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={loading}
              fullWidth
            >
              {loading ? <CircularProgress size={24} /> : 'Search'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Products Grid */}
      <Grid container spacing={3}>
        {products.map((product) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={product.product_id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardMedia
                component="img"
                height="200"
                image={product.images?.[0]?.url || '/placeholder-image.jpg'}
                alt={product.title}
                sx={{ objectFit: 'cover' }}
              />
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography gutterBottom variant="h6" component="h2" noWrap>
                  {product.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  ID: {product.product_id}
                </Typography>
                <Chip 
                  label={product.category} 
                  size="small" 
                  color="primary" 
                  sx={{ mb: 1 }}
                />
                <Typography variant="body2" color="text.secondary">
                  ₹{product.price}
                  {product.discount_price && (
                    <span style={{ textDecoration: 'line-through', marginLeft: '8px' }}>
                      ₹{product.discount_price}
                    </span>
                  )}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Stock: {product.stock_status}
                </Typography>
              </CardContent>
              <CardActions>
                <IconButton 
                  color="primary" 
                  onClick={() => handleEditProduct(product)}
                >
                  <EditIcon />
                </IconButton>
                <IconButton 
                  color="error" 
                  onClick={() => handleDeleteProduct(product.product_id)}
                >
                  <DeleteIcon />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Empty State */}
      {!loading && products.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="h6" color="text.secondary">
            No products found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search criteria or add a new product
          </Typography>
        </Box>
      )}

      {/* Add Product FAB */}
      <Fab
        color="primary"
        aria-label="add"
        onClick={handleAddProduct}
        sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
        }}
      >
        <AddIcon />
      </Fab>

      {/* Product Modal */}
      <ProductModal
        open={openModal}
        onClose={handleModalClose}
        onSave={handleProductSaved}
        product={editingProduct}
      />
    </Container>
  )
}
