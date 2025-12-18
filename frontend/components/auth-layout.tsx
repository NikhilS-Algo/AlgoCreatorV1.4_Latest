"use client"

import Image from "next/image"
import type React from "react"
import AlgoCreaterLogo from "@/public/images/AlgoCreator_Logo_v3.png"


interface AuthLayoutProps {
  children: React.ReactNode
  title: string
  subtitle: string
  backgroundVariant?: "signin" | "signup"
}

export function AuthLayout({ children, title, subtitle, backgroundVariant = "signin" }: AuthLayoutProps) {
  const bgClass =
    backgroundVariant === "signin"
      ? "bg-gradient-to-br from-blue-50 via-blue-100 to-indigo-100"
      : "bg-gradient-to-tr from-blue-100 via-indigo-50 to-blue-50"

  return (
    <div className={`min-h-screen ${bgClass} flex items-center justify-center p-6 overflow-hidden`}>
      <div className="w-full max-w-lg">
        <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl border border-white/20 p-8">
          {/* Logo and Header */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-6">
              <Image src={AlgoCreaterLogo} alt="AlgoCreator" width={70} height={70} className="object-contain" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent mb-2">
                {title}
              </h1>
              <p className="text-gray-600 text-sm">{subtitle}</p>
            </div>
          </div>

          {children}

          {/* Footer */}
          <div className="text-center mt-8">
            <p className="text-xs text-gray-500">© 2025 AlgoCreator. All rights reserved.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
