"use client"

import React from "react";
import Image from "next/image";
import AlgoCreaterLogo from "@/public/images/AlgoCreator_Logo_v3.png";
import AlgoAnalyticsLogo from "@/public/images/algologo.png";
import ProductTourShepherd from "./ProductTour";
import { useContext } from "react"
import { loginSuccess, Logout } from "@/redux/features/auth/authSlice";
import { LogOut } from "lucide-react";
import { AuthContext } from "@/components/utils/AuthProvider"

interface AuthContextType {
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const Navbar = () => {
  const authContext = useContext(AuthContext) as AuthContextType;
  const { logout } = authContext;
  
  return (
    <div className="flex w-full items-center justify-between bg-gray-50 border-b border-gray-200 shadow-sm px-4 py-2">
      <div className="flex flex-1 h-16 items-center justify-between px-4">
        <div className="flex h-full gap-2 items-center">
          <Image
            src={AlgoCreaterLogo}
            alt="AlgoCreator"
            className="h-full w-auto object-cover"
          />
          <span className="text-2xl font-semibold text-gray-800 tracking-wider">
            AlgoCreator
          </span>
        </div>
        <div className="flex h-full items-center gap-6">
          <ProductTourShepherd />
          <button
            onClick={() => logout()}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition-colors flex gap-2"
          >
            Logout
            <LogOut />
          </button>
          <Image
            src={AlgoAnalyticsLogo}
            alt="AlgoAnalitics"
            className="h-full w-auto object-cover"
          />
        </div>
      </div>
    </div>
  );
};

export default Navbar;
