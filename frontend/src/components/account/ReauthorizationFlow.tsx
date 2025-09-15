import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  AlertTriangle,
  CheckCircle,
  ExternalLink,
  Info,
  RefreshCw,
  Shield,
  XCircle,
  Clock,
  Lock,
  ArrowRight
} from 'lucide-react';
import { Account } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface ReauthorizationFlowProps {
  account: Account | null;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type ReauthStep = 'info' | 'authorize' | 'processing' | 'success' | 'error';

export const ReauthorizationFlow: React.FC<ReauthorizationFlowProps> = ({
  account,
  open,
  onClose,
  onSuccess,
}) => {
  const { toast } = useToast();
  const [currentStep, setCurrentStep] = useState<ReauthStep>('info');
  const [isProcessing, setIsProcessing] = useState(false);
  const [authorizationUrl, setAuthorizationUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const resetFlow = () => {
    setCurrentStep('info');
    setIsProcessing(false);
    setAuthorizationUrl(null);
    setError(null);
    setProgress(0);
  };

  const handleClose = () => {
    resetFlow();
    onClose();
  };

  const startReauthorization = async () => {
    if (!account) return;

    setCurrentStep('authorize');
    setIsProcessing(true);
    setProgress(25);

    try {
      const response = await accountService.reauthorizeAccount(account.id);

      // Check if the response indicates success
      if (response.status === 'success' || response.token_refreshed) {
        setProgress(75);
        setCurrentStep('processing');

        // Since reauthorize just refreshes the token, we can immediately check status
        setTimeout(() => {
          checkAuthorizationStatus();
        }, 1000);
      } else if (response.authorizationUrl) {
        // If there's an authorization URL (for future OAuth flow)
        setAuthorizationUrl(response.authorizationUrl);
        setProgress(50);

        // Open authorization URL in new window
        const authWindow = window.open(
          response.authorizationUrl,
          'amazon-auth',
          'width=800,height=600,left=200,top=100'
        );

        // Start polling for completion
        setCurrentStep('processing');
        setProgress(75);

        // Check if window is closed
        const checkInterval = setInterval(() => {
          if (authWindow && authWindow.closed) {
            clearInterval(checkInterval);
            checkAuthorizationStatus();
          }
        }, 1000);
      } else {
        throw new Error(response.message || 'Token refresh failed');
      }
    } catch (error) {
      console.error('Reauthorization failed:', error);
      setError((error as Error).message);
      setCurrentStep('error');
      setProgress(0);
    } finally {
      setIsProcessing(false);
    }
  };

  const checkAuthorizationStatus = async () => {
    if (!account) return;

    try {
      // Check if the account has been reauthorized
      const updatedAccount = await accountService.getAccountDetails(account.id);

      if (updatedAccount.status === 'healthy') {
        setProgress(100);
        setCurrentStep('success');
        
        toast({
          title: "Reauthorization successful",
          description: "Your account has been successfully reauthorized.",
        });

        if (onSuccess) {
          setTimeout(() => {
            onSuccess();
            handleClose();
          }, 2000);
        }
      } else {
        throw new Error('Authorization was not completed successfully');
      }
    } catch (error) {
      console.error('Failed to verify authorization:', error);
      setError('Failed to verify authorization. Please try again.');
      setCurrentStep('error');
      setProgress(0);
    }
  };

  const getReasonForReauth = () => {
    if (!account) return null;

    switch (account.status) {
      case 'expired':
        return {
          icon: XCircle,
          title: 'Token Expired',
          description: 'Your access token has expired and needs to be renewed to continue accessing Amazon DSP services.',
          color: 'text-red-600 dark:text-red-400'
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          title: 'Token Expiring Soon',
          description: `Your token will expire in ${account.tokenExpiresAt ? accountService.getTimeUntilExpiry(account.tokenExpiresAt) : 'unknown time'}. Reauthorize now to avoid service interruption.`,
          color: 'text-yellow-600 dark:text-yellow-400'
        };
      case 'disconnected':
        return {
          icon: Lock,
          title: 'Account Disconnected',
          description: 'This account has been disconnected and needs to be reauthorized to restore access.',
          color: 'text-gray-600 dark:text-gray-400'
        };
      default:
        return {
          icon: RefreshCw,
          title: 'Reauthorization Required',
          description: 'Your account needs to be reauthorized to continue.',
          color: 'text-blue-600 dark:text-blue-400'
        };
    }
  };

  if (!account) return null;

  const reason = getReasonForReauth();

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Reauthorize Account
          </DialogTitle>
          <DialogDescription>
            {account.accountName} - {account.marketplace?.name || account.marketplaceName || 'Unknown'}
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          {/* Progress Bar */}
          {progress > 0 && (
            <Progress value={progress} className="h-2" />
          )}

          {/* Info Step */}
          {currentStep === 'info' && reason && (
            <>
              <Alert>
                <reason.icon className={cn("h-4 w-4", reason.color)} />
                <AlertTitle>{reason.title}</AlertTitle>
                <AlertDescription className="mt-2">
                  {reason.description}
                </AlertDescription>
              </Alert>

              <div className="space-y-3">
                <h4 className="text-sm font-semibold">What will happen:</h4>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>You'll be redirected to Amazon's secure login page</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>Log in with your Amazon DSP account credentials</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>Authorize the application to access your account</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <ArrowRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>Your tokens will be automatically refreshed</span>
                  </li>
                </ul>
              </div>

              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Your existing settings and preferences will be preserved after reauthorization.
                </AlertDescription>
              </Alert>
            </>
          )}

          {/* Authorize Step */}
          {currentStep === 'authorize' && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <ExternalLink className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="space-y-2">
                <h4 className="font-semibold">Opening Amazon Authorization</h4>
                <p className="text-sm text-muted-foreground">
                  A new window will open for you to authorize with Amazon.
                </p>
                <p className="text-xs text-muted-foreground">
                  If the window doesn't open, please check your popup blocker settings.
                </p>
              </div>
              {authorizationUrl && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(authorizationUrl, 'amazon-auth')}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open Authorization Page
                </Button>
              )}
            </div>
          )}

          {/* Processing Step */}
          {currentStep === 'processing' && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <RefreshCw className="h-6 w-6 text-blue-600 dark:text-blue-400 animate-spin" />
              </div>
              <div className="space-y-2">
                <h4 className="font-semibold">Processing Authorization</h4>
                <p className="text-sm text-muted-foreground">
                  Please complete the authorization in the opened window.
                </p>
                <p className="text-xs text-muted-foreground">
                  We'll automatically detect when you've completed the authorization.
                </p>
              </div>
            </div>
          )}

          {/* Success Step */}
          {currentStep === 'success' && (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="space-y-2">
                <h4 className="font-semibold text-green-600 dark:text-green-400">
                  Authorization Successful!
                </h4>
                <p className="text-sm text-muted-foreground">
                  Your account has been successfully reauthorized and tokens have been refreshed.
                </p>
              </div>
            </div>
          )}

          {/* Error Step */}
          {currentStep === 'error' && (
            <div className="space-y-4">
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Authorization Failed</AlertTitle>
                <AlertDescription className="mt-2">
                  {error || 'Failed to complete reauthorization. Please try again.'}
                </AlertDescription>
              </Alert>
              
              <div className="space-y-2 text-sm">
                <p className="font-medium">Troubleshooting tips:</p>
                <ul className="space-y-1 text-muted-foreground list-disc list-inside">
                  <li>Check your internet connection</li>
                  <li>Ensure popup blockers are disabled for this site</li>
                  <li>Verify your Amazon DSP credentials are correct</li>
                  <li>Make sure you have the necessary permissions</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          {currentStep === 'info' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={startReauthorization} disabled={isProcessing}>
                <Shield className="h-4 w-4 mr-2" />
                Start Reauthorization
              </Button>
            </>
          )}
          
          {currentStep === 'error' && (
            <>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={() => setCurrentStep('info')}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
            </>
          )}
          
          {(currentStep === 'authorize' || currentStep === 'processing') && (
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          )}
          
          {currentStep === 'success' && (
            <Button onClick={handleClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};