import { useState, useCallback, useRef } from "react";
import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from "axios";

interface UseAxiosResult<T> {
  data: T | null;
  error: string | null;
  loaded: boolean;
  callAPI: (
    url: string,
    method?: AxiosRequestConfig["method"],
    payload?: any,
    headers?: Record<string, string>,
    responseType?: AxiosRequestConfig["responseType"]
  ) => Promise<void>;
  cancel: () => void;
}

export const useAxios = <T = any>(): UseAxiosResult<T> => {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState<boolean>(false);
  const controllerRef = useRef<AbortController | null>(null);

  const cancel = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
  };

  const callAPI = useCallback(
    async (
      url: string,
      method: AxiosRequestConfig["method"] = "GET",
      payload: any = {},
      headers: Record<string, string> = {},
      responseType: AxiosRequestConfig["responseType"] = "json"
    ) => {
      setLoaded(false);
      setError(null);
      setData(null);

      if (controllerRef.current) {
        controllerRef.current.abort();
      }

      controllerRef.current = new AbortController();

      try {
        const response: AxiosResponse<T> = await axios({
          url,
          method,
          data: payload,
          headers: {
            "Content-Type": "application/json",
            ...headers,
          },
          responseType,
          signal: controllerRef.current.signal,
        });
        console.log(response.data);
        

        setData(response.data);
      } catch (err) {
        const axiosError = err as AxiosError;

        if (axios.isCancel(err)) {
          console.log("Request canceled:", axiosError.message);
        } else {
          setError(axiosError.message || "Something went wrong");
        }
      } finally {
        setLoaded(true);
      }
    },
    []
  );

  return {
    data,
    error,
    loaded,
    callAPI,
    cancel,
  };
};
