import React, { useState, useEffect } from 'react'
import {
  Box,
  TextField,
  Button,
  Typography,
  IconButton,
  Divider,
  Alert,
  Paper,
  Grid
} from '@mui/material'
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material'


export default function SpecificationsInput({ value, onChange, error, helperText }) {
  const [specs, setSpecs] = useState([])

  useEffect(() => {
    if (value) {
      try {
        const parsed = typeof value === 'string' ? JSON.parse(value) : value
        const specsArray = Object.entries(parsed).map(([key, val]) => ({
          key,
          value: val
        }))
        setSpecs(specsArray)
      } catch (e) {
        // If parsing fails, start with empty array
        setSpecs([])
      }
    }
  }, [value])

  const handleSpecChange = (index, field, newValue) => {
    const newSpecs = [...specs]
    newSpecs[index][field] = newValue
    setSpecs(newSpecs)
    updateParent(newSpecs)
  }

  const addSpec = () => {
    const newSpecs = [...specs, { key: '', value: '' }]
    setSpecs(newSpecs)
    updateParent(newSpecs)
  }

  const removeSpec = (index) => {
    const newSpecs = specs.filter((_, i) => i !== index)
    setSpecs(newSpecs)
    updateParent(newSpecs)
  }

  const updateParent = (specsArray) => {
    const specsObject = specsArray.reduce((acc, spec) => {
      if (spec.key && spec.value) {
        acc[spec.key] = spec.value
      }
      return acc
    }, {})
    
    onChange(JSON.stringify(specsObject, null, 2))
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="medium">
          Product Specifications
        </Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<AddIcon />}
          onClick={addSpec}
        >
          Add Specification
        </Button>
      </Box>

      {specs.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center', bgcolor: 'grey.50' }}>
          <Typography variant="body2" color="text.secondary">
            No specifications added yet. Click "Add Specification" to get started.
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ space: 2 }}>
          {specs.map((spec, index) => (
            <Box key={index}>
              <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                <Grid item xs={12} sm={5}>
                  <TextField
                    fullWidth
                    label="Specification Name"
                    placeholder="e.g., Battery Life, Screen Size, Weight"
                    value={spec.key}
                    onChange={(e) => handleSpecChange(index, 'key', e.target.value)}
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Value"
                    placeholder="e.g., 8 hours, 6.1 inches, 200g"
                    value={spec.value}
                    onChange={(e) => handleSpecChange(index, 'value', e.target.value)}
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={1}>
                  <IconButton
                    color="error"
                    onClick={() => removeSpec(index)}
                    size="small"
                  >
                    <DeleteIcon />
                  </IconButton>
                </Grid>
              </Grid>
              {index < specs.length - 1 && <Divider sx={{ mb: 2 }} />}
            </Box>
          ))}
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {helperText && !error && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {helperText}
        </Typography>
      )}

      {/* Preview */}
      {specs.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Preview:
          </Typography>
          <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
            {specs.map((spec, index) => (
              <Typography key={index} variant="body2" sx={{ mb: 0.5 }}>
                <strong>{spec.key || 'Specification Name'}:</strong> {spec.value || 'Value'}
              </Typography>
            ))}
          </Paper>
        </Box>
      )}
    </Box>
  )
}