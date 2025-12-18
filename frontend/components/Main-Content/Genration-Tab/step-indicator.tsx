"use client"

interface StepIndicatorProps {
  steps: string[]
  currentStep: number
  onStepClick: (step: number) => void
  completedSteps: Set<number>
}

export function StepIndicator({ steps, currentStep, onStepClick, completedSteps }: StepIndicatorProps) {
  return (
    <div className="w-full px-6 py-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={index} className="flex items-center flex-1">
            {/* Step Circle */}
            <button
              onClick={() => onStepClick(index)}
              className={`flex items-center justify-center w-12 h-12 rounded-full font-semibold text-sm transition-all cursor-pointer ${
                index === currentStep
                  ? "bg-primary text-primary-foreground shadow-lg scale-110"
                  : completedSteps.has(index)
                    ? "bg-accent text-accent-foreground"
                    : "bg-input text-muted-foreground hover:bg-input/80"
              }`}
            >
              {completedSteps.has(index) ? "✓" : index + 1}
            </button>

            {/* Connecting Line */}
            {index < steps.length - 1 && (
              <div
                className={`flex-1 h-1 mx-2 rounded-full transition-colors ${
                  completedSteps.has(index) ? "bg-accent" : "bg-input"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Labels */}
      <div className="flex justify-between mt-4 px-2">
        {steps.map((step, index) => (
          <div key={index} className="flex-1 text-center">
            <p
              className={`text-xs font-medium ${
                index === currentStep
                  ? "text-primary"
                  : completedSteps.has(index)
                    ? "text-accent"
                    : "text-muted-foreground"
              }`}
            >
              {step}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
