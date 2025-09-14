import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { 
  CheckCircle, 
  AlertCircle, 
  RefreshCw,
  ShoppingBag,
  ArrowRight,
  Globe,
  DollarSign
} from 'lucide-react'

interface CallbackResult {
  success: boolean
  user_id?: string
  profiles?: number
  error?: string
  error_description?: string
}

export function AmazonOAuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [isProcessing, setIsProcessing] = useState(true)
  const [result, setResult] = useState<CallbackResult | null>(null)

  useEffect(() => {
    processCallback()
  }, [searchParams])

  const processCallback = async () => {
    try {
      // Check for success/error in URL params
      const success = searchParams.get('success')
      const error = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')
      const userId = searchParams.get('user_id')
      const profileCount = searchParams.get('profiles')

      if (success === 'true') {
        setResult({
          success: true,
          user_id: userId || undefined,
          profiles: profileCount ? parseInt(profileCount, 10) : undefined
        })
      } else if (error) {
        setResult({
          success: false,
          error,
          error_description: errorDescription || undefined
        })
      } else {
        // Check for OAuth callback parameters (code, state, error)
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const oauthError = searchParams.get('error')

        if (oauthError) {
          setResult({
            success: false,
            error: oauthError,
            error_description: searchParams.get('error_description') || undefined
          })
        } else if (code && state) {
          // Process OAuth callback
          await processOAuthCallback(code, state)
        } else {
          setResult({
            success: false,
            error: 'invalid_request',
            error_description: 'Missing required callback parameters'
          })
        }
      }
    } catch (err) {
      console.error('Callback processing error:', err)
      setResult({
        success: false,
        error: 'processing_error',
        error_description: 'Failed to process OAuth callback'
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const processOAuthCallback = async (code: string, state: string) => {
    try {
      const response = await fetch('/api/v1/auth/amazon/connect/callback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ code, state }).toString(),
      })

      if (response.ok) {
        // Should redirect automatically, but handle success case
        setResult({
          success: true,
        })
      } else {
        const errorData = await response.json()
        setResult({
          success: false,
          error: errorData.error?.code || 'callback_failed',
          error_description: errorData.error?.message || 'Failed to process callback'
        })
      }
    } catch (err) {
      setResult({
        success: false,
        error: 'network_error',
        error_description: 'Network error during callback processing'
      })
    }
  }

  const continueToDashboard = () => {
    navigate('/dashboard')
  }

  const retryConnection = () => {
    navigate('/dashboard?tab=connections')
  }

  if (isProcessing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center">
              <RefreshCw className="h-6 w-6 text-purple-600 dark:text-purple-400 animate-spin" />
            </div>
            <CardTitle>Processing Connection</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-muted-foreground mb-4">
              We're processing your Amazon account connection...
            </p>
            <div className="space-y-2">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-purple-600 rounded-full animate-pulse" style={{ width: '60%' }} />
              </div>
              <p className="text-sm text-muted-foreground">Please wait a moment</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 h-12 w-12 bg-muted rounded-full flex items-center justify-center">
              <AlertCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <CardTitle>Processing...</CardTitle>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        {result.success ? (
          <>
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 h-12 w-12 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <CardTitle className="text-green-600 dark:text-green-400">
                Connection Successful!
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
                <ShoppingBag className="h-4 w-4" />
                <AlertDescription>
                  Your Amazon advertising account has been successfully connected.
                  {result.profiles && (
                    <span className="block mt-1 font-medium">
                      Connected {result.profiles} profile{result.profiles > 1 ? 's' : ''}
                    </span>
                  )}
                </AlertDescription>
              </Alert>

              {result.profiles && result.profiles > 0 && (
                <div className="space-y-3">
                  <h4 className="font-medium text-sm">What you can do now:</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <div className="h-1.5 w-1.5 bg-purple-600 rounded-full" />
                      Access campaign performance data
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <div className="h-1.5 w-1.5 bg-purple-600 rounded-full" />
                      Generate detailed reports and insights
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <div className="h-1.5 w-1.5 bg-purple-600 rounded-full" />
                      Monitor account health and token status
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Button 
                  onClick={continueToDashboard} 
                  className="flex-1 flex items-center gap-2"
                >
                  Continue to Dashboard
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </>
        ) : (
          <>
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 h-12 w-12 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <CardTitle className="text-red-600 dark:text-red-400">
                Connection Failed
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-1">
                    <div className="font-medium">
                      {getErrorTitle(result.error)}
                    </div>
                    <div className="text-sm">
                      {result.error_description || getErrorDescription(result.error)}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>

              <div className="space-y-3">
                <h4 className="font-medium text-sm">How to resolve:</h4>
                <div className="space-y-2 text-sm text-muted-foreground">
                  {getErrorSolutions(result.error).map((solution, index) => (
                    <div key={index} className="flex items-start gap-2">
                      <div className="h-1.5 w-1.5 bg-muted-foreground rounded-full mt-2 flex-shrink-0" />
                      <span>{solution}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Button 
                  onClick={retryConnection} 
                  variant="outline" 
                  className="flex-1"
                >
                  Try Again
                </Button>
                <Button 
                  onClick={continueToDashboard} 
                  className="flex-1"
                >
                  Go to Dashboard
                </Button>
              </div>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  )
}

function getErrorTitle(error?: string): string {
  switch (error) {
    case 'access_denied':
      return 'Access Denied'
    case 'invalid_request':
      return 'Invalid Request'
    case 'invalid_grant':
      return 'Authorization Expired'
    case 'server_error':
      return 'Server Error'
    case 'temporarily_unavailable':
      return 'Service Temporarily Unavailable'
    case 'network_error':
      return 'Network Error'
    case 'processing_error':
      return 'Processing Error'
    default:
      return 'Connection Error'
  }
}

function getErrorDescription(error?: string): string {
  switch (error) {
    case 'access_denied':
      return 'You denied permission to access your Amazon account'
    case 'invalid_request':
      return 'The connection request was malformed or missing required parameters'
    case 'invalid_grant':
      return 'The authorization code has expired or is invalid'
    case 'server_error':
      return 'Amazon encountered an error processing your request'
    case 'temporarily_unavailable':
      return 'Amazon services are temporarily unavailable'
    case 'network_error':
      return 'Unable to communicate with Amazon servers'
    case 'processing_error':
      return 'An error occurred while processing your connection'
    default:
      return 'An unexpected error occurred during the connection process'
  }
}

function getErrorSolutions(error?: string): string[] {
  switch (error) {
    case 'access_denied':
      return [
        'Make sure you click "Allow" when prompted by Amazon',
        'Ensure you have the necessary permissions on your Amazon account',
        'Try the connection process again'
      ]
    case 'invalid_request':
    case 'processing_error':
      return [
        'Clear your browser cache and cookies',
        'Try using a different browser',
        'Contact support if the issue persists'
      ]
    case 'invalid_grant':
      return [
        'The authorization code has expired',
        'Start the connection process again',
        'Complete the process more quickly to avoid expiration'
      ]
    case 'server_error':
    case 'temporarily_unavailable':
      return [
        'Amazon services may be experiencing issues',
        'Wait a few minutes and try again',
        'Check Amazon\'s service status page'
      ]
    case 'network_error':
      return [
        'Check your internet connection',
        'Disable any VPN or proxy that might interfere',
        'Try again in a few minutes'
      ]
    default:
      return [
        'Refresh the page and try again',
        'Clear your browser cache',
        'Contact support if the problem continues'
      ]
  }
}