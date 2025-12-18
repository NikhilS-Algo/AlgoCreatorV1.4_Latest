"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useSelector } from "react-redux"
import { selectAuth } from "@/redux/features/auth/authSlice" // Import the new selector

import SignIn from "./login/sign-in"
import SignUp from "./login/sign-up"
import { Button } from "@/components/ui/button"
import SpinnerLoader from "@/components/ui/SpinnerLoader"


export default function Page() {
  const [currentPage, setCurrentPage] = useState<"signin" | "signup">("signin")
  const { token } = useSelector(selectAuth) // Use the selectAuth selector
  const router = useRouter()

  useEffect(() => {
    if (token) {
      router.push('/dashboard')
    }
  }, [token, router])

  if (token) {
    return (
      <div className="flex justify-center items-center h-screen w-screen">
        <SpinnerLoader />
      </div>
    )
  }

  return (
    <div>
      {/* Navigation for demo purposes */}
      <div className="fixed top-4 right-4 z-50 flex gap-2">
        <Button
          onClick={() => setCurrentPage("signin")}
          variant={currentPage === "signin" ? "default" : "outline"}
          size="sm"
          id="sign-in-btn"
        >
          Sign In
        </Button>
        <Button
          onClick={() => setCurrentPage("signup")}
          variant={currentPage === "signup" ? "default" : "outline"}
          size="sm"
        >
          Sign Up
        </Button>
      </div>

      {currentPage === "signin" ? (
        <SignIn onNavigateToSignUp={() => setCurrentPage("signup")} />
      ) : (
        <SignUp onNavigateToSignIn={() => setCurrentPage("signin")} />
      )}
    </div>
  )
}
