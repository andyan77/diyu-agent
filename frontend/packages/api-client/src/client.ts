import axios, { type AxiosInstance, type AxiosRequestConfig } from "axios";

export interface ApiClient {
  instance: AxiosInstance;
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T>;
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>;
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>;
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>;
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T>;
}

export function createApiClient(baseURL: string, token?: string): ApiClient {
  const instance = axios.create({
    baseURL,
    timeout: 30_000,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  return {
    instance,
    async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
      const res = await instance.get<T>(url, config);
      return res.data;
    },
    async post<T>(
      url: string,
      data?: unknown,
      config?: AxiosRequestConfig,
    ): Promise<T> {
      const res = await instance.post<T>(url, data, config);
      return res.data;
    },
    async put<T>(
      url: string,
      data?: unknown,
      config?: AxiosRequestConfig,
    ): Promise<T> {
      const res = await instance.put<T>(url, data, config);
      return res.data;
    },
    async patch<T>(
      url: string,
      data?: unknown,
      config?: AxiosRequestConfig,
    ): Promise<T> {
      const res = await instance.patch<T>(url, data, config);
      return res.data;
    },
    async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
      const res = await instance.delete<T>(url, config);
      return res.data;
    },
  };
}
