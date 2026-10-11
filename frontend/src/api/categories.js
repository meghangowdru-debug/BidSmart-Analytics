import apiClient from './client';

export const categoriesApi = {
  // Public list of all categories with item counts
  listCategories: async () => {
    const response = await apiClient.get('/categories');
    return response.data;
  },

  // Get category details by ID
  getCategory: async (categoryId) => {
    const response = await apiClient.get(`/categories/${categoryId}`);
    return response.data;
  },
};
