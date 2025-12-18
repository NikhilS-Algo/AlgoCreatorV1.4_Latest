"use client"

interface ProgressBarProps {
  currentStep: number
  totalSteps: number
  steps: string[]
  onStepClick?: (step: number) => void
  completedSteps?: Set<number>
}

export function ProgressBar({
  currentStep,
  totalSteps,
  steps,
  onStepClick,
  completedSteps = new Set(),
}: ProgressBarProps) {
  const progressPercentage = ((currentStep + 1) / totalSteps) * 100

  return (
    <div className="w-full space-y-6 mb-8">
      {/* Progress Bar */}
      <div className="w-full h-1.5 bg-blue-50 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      <div className="flex items-center justify-between px-4">
        {steps.map((step, index) => (
          <button
            key={index}
            onClick={() => onStepClick?.(index)}
            disabled={!completedSteps.has(index) && index !== currentStep}
            className={`flex flex-col items-center gap-1 transition-all duration-200 ${index === currentStep
                ? "cursor-pointer"
                : completedSteps.has(index)
                  ? "cursor-pointer hover:opacity-80"
                  : "cursor-not-allowed opacity-50"
              }`}
          >
            <span
              className={`text-xs font-medium transition-colors ${index <= currentStep ? "text-blue-600" : "text-gray-400"
                }`}
            >
              {step}
            </span>
            {index === currentStep && (
              <div className="h-0.5 w-6 bg-blue-600 rounded-full" />
            )}
          </button>
        ))}
      </div>
    </div>
  )
}
