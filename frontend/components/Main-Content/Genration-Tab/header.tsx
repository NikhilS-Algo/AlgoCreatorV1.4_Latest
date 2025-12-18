import { Sparkles } from "lucide-react"

export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg flex items-center justify-center">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Presenton</h1>
          <span className="ml-2 px-2.5 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">BETA</span>
        </div>
        <nav className="flex items-center gap-8">
          <a href="#" className="text-sm text-gray-600 hover:text-gray-900">
            Create Template
          </a>
          <a href="#" className="text-sm text-gray-600 hover:text-gray-900">
            API Docs
          </a>
          <a href="#" className="text-sm text-gray-600 hover:text-gray-900">
            All Templates
          </a>
          <a href="#" className="text-sm text-gray-600 hover:text-gray-900">
            Dashboard
          </a>
          <button className="w-9 h-9 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center">
            <span className="text-sm">👤</span>
          </button>
        </nav>
      </div>
    </header>
  )
}
