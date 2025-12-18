"use client"

import type React from "react"

import { useState, useContext } from "react"
import Link from "next/link"
import { Eye, EyeOff, Mail, Lock, User, Phone, CheckCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { AuthLayout } from "@/components/auth-layout"
import { FormField } from "@/components/form-field"
import { AuthContext } from "@/components/utils/AuthProvider"

interface SignUpProps {
  onNavigateToSignIn?: () => void
}

interface AuthContextType {
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export default function SignUp({ onNavigateToSignIn }: SignUpProps) {
  const authContext = useContext(AuthContext) as AuthContextType;
    const { signup } = authContext;
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    mobile: "",
    password: "",
  })
  const [agreeToTerms, setAgreeToTerms] = useState(false)

  const updateFormData = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log("Sign up:", { ...formData, agreeToTerms })
    signup(formData.email, formData.password);
  }

  return (
    <AuthLayout
      title="Sign UP"
      subtitle="Create your account and start building amazing presentations"
      backgroundVariant="signup"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 gap-5">
          <FormField
            id="fullName"
            label="Full Name"
            placeholder="Enter your full name"
            value={formData.fullName}
            onChange={(value) => updateFormData("fullName", value)}
            required
            icon={<User className="h-5 w-5" />}
          />

          <FormField
            id="email"
            label="Email Address"
            type="email"
            placeholder="Enter your email"
            value={formData.email}
            onChange={(value) => updateFormData("email", value)}
            required
            icon={<Mail className="h-5 w-5" />}
          />

          <FormField
            id="mobile"
            label="Mobile Number"
            type="tel"
            placeholder="Enter your mobile number"
            value={formData.mobile}
            onChange={(value) => updateFormData("mobile", value)}
            icon={<Phone className="h-5 w-5" />}
          />

          <FormField
            id="password"
            label="Password"
            type={showPassword ? "text" : "password"}
            placeholder="Create a strong password"
            value={formData.password}
            onChange={(value) => updateFormData("password", value)}
            required
            icon={<Lock className="h-5 w-5" />}
            rightIcon={showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            onRightIconClick={() => setShowPassword(!showPassword)}
          />
        </div>

        {/* Password Requirements */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-700 font-medium mb-3">Password must contain:</p>
          <div className="grid grid-cols-2 gap-2">
            {["At least 8 characters", "One uppercase letter", "One lowercase letter", "One number"].map(
              (req, index) => (
                <div key={index} className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-blue-500 flex-shrink-0" />
                  <span className="text-sm text-blue-600">{req}</span>
                </div>
              ),
            )}
          </div>
        </div>

        {/* Terms and Conditions */}
        <div className="flex items-start space-x-3">
          <Checkbox
            id="terms"
            checked={agreeToTerms}
            onCheckedChange={(checked) => setAgreeToTerms(checked as boolean)}
            className="mt-1"
          />
          <Label htmlFor="terms" className="text-sm text-gray-600 leading-relaxed">
            I agree to the{" "}
            <Link href="/terms" className="text-blue-600 hover:text-blue-800 font-medium">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-blue-600 hover:text-blue-800 font-medium">
              Privacy Policy
            </Link>
            <span className="text-red-500 ml-1">*</span>
          </Label>
        </div>

        <Button
          type="submit"
          // disabled={!agreeToTerms}
          disabled={true}
          className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl disabled:shadow-none group"
        >
          Create Account
          <CheckCircle className="ml-2 h-4 w-4 group-hover:scale-110 transition-transform" />
        </Button>
      </form>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          {/* <span className="px-4 bg-white text-gray-500">Or sign up with</span> */}
        </div>
      </div>

      {/* Social Signup */}
      {/* <div className="grid grid-cols-1 gap-4">
        <Button
          variant="outline"
          className="h-12 border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition-all duration-200 bg-transparent"
          type="button"
        >
          <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </Button>
      </div> */}

      {/* Sign In Link */}
      <div className="text-center mt-6">
        <p className="text-sm text-gray-600">
          Already have an account?{" "}
          <button
            type="button"
            onClick={onNavigateToSignIn}
            className="text-blue-600 hover:text-blue-800 font-semibold transition-colors underline-offset-4 hover:underline"
          >
            Sign in here
          </button>
        </p>
      </div>
    </AuthLayout>
  )
}
