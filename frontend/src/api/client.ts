/// <reference types="vite/client" />
import axios from "axios";

// Use environment variable or fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: `${API_BASE_URL}/v1`,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`→ ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error("Request error:", error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`← ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.response) {
      console.error("Response error:", error.response.status, error.response.data);
    } else if (error.request) {
      console.error("No response received:", error.message);
    } else {
      console.error("Request setup error:", error.message);
    }
    return Promise.reject(error);
  }
);