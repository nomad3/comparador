import axios from 'axios';

// Obtener la URL base de la API desde las variables de entorno de Vite
// VITE_API_BASE_URL se define en .env y/o en la config de Docker Compose
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

console.log("API Base URL:", API_BASE_URL); // Para depuración

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // Puedes añadir otros headers aquí si son necesarios (ej: Authorization)
  },
  timeout: 10000, // Timeout de 10 segundos para las peticiones
});

// Opcional: Interceptores para manejar errores globales o añadir tokens
apiClient.interceptors.response.use(
  (response) => response, // Simplemente retorna la respuesta si es exitosa
  (error) => {
    // Manejo básico de errores
    console.error('API call error:', error.response || error.message || error);

    // Podrías añadir lógica más específica aquí
    // ej: Redirigir a login si hay un 401 Unauthorized

    // Rechaza la promesa para que el error pueda ser capturado por el llamador
    return Promise.reject(error);
  }
);

export default apiClient;
