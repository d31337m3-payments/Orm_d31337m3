import axios from "axios";

const envBase = process.env.REACT_APP_BACKEND_URL;
const runtimeBase = typeof window !== "undefined" ? window.location.origin : "";
const BACKEND_URL = (envBase || runtimeBase || "").replace(/\/$/, "");
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

const client = axios.create({ baseURL: API });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("d31337m3_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default client;
