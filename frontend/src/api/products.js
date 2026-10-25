import apiClient from './client';

export const productsApi = {
  // Public or filtered list of products
  listProducts: async (params = {}) => {
    const response = await apiClient.get('/products', { params });
    return response.data;
  },

  // Seller: list authenticated seller's own inventory
  listMyProducts: async (params = {}) => {
    const response = await apiClient.get('/products/seller/me', { params });
    return response.data;
  },

  // Get product by ID
  getProduct: async (productId) => {
    const response = await apiClient.get(`/products/${productId}`);
    return response.data;
  },

  // Seller: create a new product catalog item
  createProduct: async (productData) => {
    const response = await apiClient.post('/products', productData);
    return response.data;
  },

  // Seller: update an existing product
  updateProduct: async (productId, productData) => {
    const response = await apiClient.put(`/products/${productId}`, productData);
    return response.data;
  },

  // Seller: delete an existing product (only if no active auctions)
  deleteProduct: async (productId) => {
    const response = await apiClient.delete(`/products/${productId}`);
    return response.data;
  },
};
