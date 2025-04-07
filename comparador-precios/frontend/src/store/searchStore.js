import { create } from 'zustand';
import apiClient from '../services/apiClient';

const useSearchStore = create((set, get) => ({
  query: '',
  results: [],
  isLoading: false,
  error: null,
  message: null, // Mensaje informativo desde el backend (ej: scraping iniciado)
  jobId: null,   // ID del job de scraping si se inició uno

  setQuery: (query) => set({ query }),

  searchProducts: async (forceRefresh = false) => {
    const currentQuery = get().query;
    if (!currentQuery || currentQuery.length < 3) {
      set({ error: 'La búsqueda debe tener al menos 3 caracteres.', results: [], isLoading: false, message: null, jobId: null });
      return;
    }

    set({ isLoading: true, error: null, message: null, jobId: null, results: [] }); // Limpiar resultados anteriores al buscar

    try {
      const response = await apiClient.get('/search/', {
        params: {
          query: currentQuery,
          force_refresh: forceRefresh,
        },
      });

      console.log("API Response:", response.data); // Para depuración

      // Formatear fechas si es necesario (ej: para mostrar)
      const formattedResults = response.data.results.map(item => ({
        ...item,
        scraped_at: new Date(item.scraped_at).toLocaleString('es-CL'), // Formato local
      }));

      set({
        results: formattedResults,
        isLoading: false,
        message: response.data.message,
        jobId: response.data.job_id,
        error: null, // Limpiar error si la búsqueda fue exitosa
      });

    } catch (error) {
      console.error('Error fetching search results:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Ocurrió un error al buscar.';
      set({
        error: errorMessage,
        isLoading: false,
        results: [], // Limpiar resultados en caso de error
        message: null,
        jobId: null,
      });
    }
  },

  // Acción para forzar el refresh (iniciar scraping)
  forceSearch: () => {
    get().searchProducts(true); // Llama a searchProducts con forceRefresh=true
  },

  clearSearch: () => set({ query: '', results: [], isLoading: false, error: null, message: null, jobId: null }),
}));

export default useSearchStore;
