"use client";

import React, {
  createContext,
  useState,
  useEffect,
  useRef,
  FC,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { useAxios } from "../../hooks/useAxios";
import {
  loginSuccess,
  Logout,
  selectAuth,
} from "@/redux/features/auth/authSlice";
import { useDispatch, useSelector } from "react-redux";
import CryptoJS from "crypto-js";
import { jwtDecode } from "jwt-decode";
import Cookies from "js-cookie";
import { useToast } from "@/hooks/use-toast";

export const dynamic = "force-dynamic";


interface UserLoginResponse {
  token: string;
  email: string;
}

interface TokenPayload {
  exp: number;
}

interface AuthContextType {
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const { toast } = useToast();
  const logoutTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { token } = useSelector(selectAuth);
  const [lastAction, setLastAction] = useState<string | null>(null);
  const {
    data: userLoginData,
    error: errorUserLogin,
    loaded: loadedUserLogin,
    callAPI: callAPIUserLogin,
  } = useAxios<UserLoginResponse>();

  const {
    data: userRegisterData,
    error: errorUserRegister,
    loaded: loadedUserRegister,
    callAPI: callAPIUserRegister,
  } = useAxios();


  const dispatch = useDispatch();
  const router = useRouter();

  const UserLoginURL = process.env.NEXT_PUBLIC_LOGIN_API_URL;

  const UserSignupURL = process.env.NEXT_PUBLIC_REGISTER_API_URL;

  const login = async (username: string, password: string) => {
    setLastAction("login");
    const passwordHash = CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex);
    const body = {
      email: username,
      passwordHash: passwordHash,
      scope: ["default"],
    };
    try {
      if(UserLoginURL) {
        await callAPIUserLogin(UserLoginURL, "POST", JSON.stringify(body), {
          "Content-Type": "application/x-www-form-urlencoded",
        });
      }
      else {
        console.log("No login URL");
        
      }
    } catch (error) {
      console.error("Login error:", error);
    }
  };

  const signup = async (username: string, password: string) => {
    setLastAction("signup");
    const passwordHash = CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex);
    const body = {
      email: username,
      passwordHash: passwordHash,
      scope: ["default"],
    };

    try {
      if(UserSignupURL) {
        await callAPIUserRegister(UserSignupURL, "POST", JSON.stringify(body), {
          "Content-Type": "application/x-www-form-urlencoded",
        });
      }
    } catch (error) {
      console.error("Signup error:", error);
    }
  };

  const logout = () => {
    if (logoutTimerRef.current) {
      clearTimeout(logoutTimerRef.current);
      logoutTimerRef.current = null;
    }
    dispatch(Logout());
    Cookies.remove("token");
    localStorage.setItem("auth-logout", Date.now().toString());
    router.push("/");
  };

  useEffect(() => {
    if (loadedUserLogin) {
      if (!errorUserLogin && userLoginData) {
        try {
          const { exp } = jwtDecode<TokenPayload>(userLoginData.token);
          console.log("Login Completed");

          dispatch(
            loginSuccess({
              token: userLoginData.token,
              username: userLoginData.email,
              exp: exp,
            })
          );
          toast({
            variant: "default",
            title: "Login Success",
            description: "Welcome to AlgoCreator.",
            duration: 2000,
          });
          Cookies.set("token", userLoginData.token, {
            expires: new Date(exp * 1000),
          });
          router.push("/dashboard");
        } catch (err) {
          console.error("Error decoding token:", err);
        }
      } else {
        console.log("Login Failed");
        toast({
          variant: "destructive",
          title: "Login Failed",
          description: "Incorrect credentials.",
          duration: 3000,
        });
      }
    }
  }, [loadedUserLogin, errorUserLogin, userLoginData, dispatch, router, toast]);

  useEffect(() => {
    if (loadedUserRegister) {
      if (!errorUserRegister && userRegisterData) {
        console.log("Sign up data: ", userRegisterData);
        try {
          console.log("Sign Up Completed");
          toast({
            variant: "default",
            title: "Sign Up Success",
            description: "Login to continue.",
            duration: 3000,
            });
            document.getElementById("sign-in-btn")?.click();
        } catch (err) {
          console.error("Error decoding token:", err);
        }
      }
      else {
        console.log("Sign Up Failed");
        toast({
          variant: "destructive",
          title: "Sign Up Failed",
          description: "User Already Exists.",
          duration: 2000,
        });
      }
    }
  }, [loadedUserRegister, errorUserRegister, userRegisterData, dispatch, router, toast])

  useEffect(() => {
    if (token) {
      try {
        const { exp } = jwtDecode<TokenPayload>(token);
        if (Date.now() >= exp * 1000) {
          logout();
          return;
        }
        const remainingTime = exp * 1000 - Date.now();
        logoutTimerRef.current = setTimeout(() => {
          logout();
        }, remainingTime);
      } catch (err) {
        console.error("Error decoding token:", err);
        logout();
      }
    }
  }, [token, logout]);

  useEffect(() => {
    const handleStorageChange = () => {
      const tokenInCookie = Cookies.get("token");
      if (!tokenInCookie) {
        dispatch(Logout());
      }
    };

    window.addEventListener("storage", handleStorageChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [dispatch]);

  return (
    <AuthContext.Provider value={{ token, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
