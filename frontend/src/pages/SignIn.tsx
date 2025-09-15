import { SignIn } from '@clerk/clerk-react'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'

export function SignInPage() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isSignedIn) {
      navigate('/dashboard')
    }
  }, [isSignedIn, navigate])

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 flex flex-col items-center justify-center p-6">
      {/* Logo and Branding */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center space-x-3 mb-4">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-lg">NM</span>
          </div>
          <h1 className="text-3xl font-bold text-foreground">neverMEH</h1>
        </div>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">
          Streamline your Amazon advertising campaigns with powerful analytics and automation
        </p>
      </div>

      {/* Clerk Sign In Component */}
      <div className="w-full max-w-md">
        <SignIn 
          routing="path"
          path="/sign-in"
          redirectUrl="/dashboard"
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "shadow-xl border-0 bg-background/80 backdrop-blur-sm",
              headerTitle: "text-2xl font-bold text-foreground",
              headerSubtitle: "text-muted-foreground",
              socialButtonsBlockButton: "bg-background border-2 border-border hover:bg-muted transition-colors",
              socialButtonsBlockButtonText: "text-foreground font-medium",
              formButtonPrimary: "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white border-0 shadow-lg transition-all duration-200 transform hover:scale-[1.02]",
              formFieldInput: "bg-background border-2 border-border focus:border-purple-500 transition-colors",
              footerActionLink: "text-purple-600 hover:text-purple-700 font-medium"
            },
            variables: {
              colorPrimary: "#8b5cf6",
              colorBackground: "hsl(var(--background))",
              colorText: "hsl(var(--foreground))",
              colorTextSecondary: "hsl(var(--muted-foreground))",
              colorInputBackground: "hsl(var(--background))",
              colorInputText: "hsl(var(--foreground))",
              borderRadius: "0.5rem"
            }
          }}
        />
      </div>

      {/* Features */}
      <div className="mt-12 max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-6 bg-background/50 rounded-xl border backdrop-blur-sm">
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Real-time Analytics</h3>
            <p className="text-muted-foreground text-sm">
              Monitor campaign performance with live data and actionable insights
            </p>
          </div>
          
          <div className="text-center p-6 bg-background/50 rounded-xl border backdrop-blur-sm">
            <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/20 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Multi-Account Management</h3>
            <p className="text-muted-foreground text-sm">
              Seamlessly manage multiple Amazon accounts from one dashboard
            </p>
          </div>
          
          <div className="text-center p-6 bg-background/50 rounded-xl border backdrop-blur-sm">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Automated Optimization</h3>
            <p className="text-muted-foreground text-sm">
              Let AI optimize your campaigns for better performance and ROI
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-12 text-center text-sm text-muted-foreground">
        <p>&copy; 2024 neverMEH. Built with security and performance in mind.</p>
      </div>
    </div>
  )
}