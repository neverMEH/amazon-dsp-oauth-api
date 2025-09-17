import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function Callback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const success = searchParams.get('success');
    const error = searchParams.get('error');
    const state = searchParams.get('state');

    if (success === 'true') {
      // OAuth was successful - notify the parent window if it exists
      if (window.opener && !window.opener.closed) {
        window.opener.postMessage({
          type: 'oauth-success',
          state: state
        }, window.location.origin);

        // Close this window after a short delay
        setTimeout(() => {
          window.close();
        }, 1000);
      } else {
        // If no opener, redirect to accounts page
        navigate('/accounts');
      }
    } else if (error) {
      // OAuth failed - notify the parent window
      if (window.opener && !window.opener.closed) {
        window.opener.postMessage({
          type: 'oauth-error',
          error: error
        }, window.location.origin);

        setTimeout(() => {
          window.close();
        }, 1000);
      } else {
        // If no opener, redirect to accounts with error
        navigate('/accounts?error=' + encodeURIComponent(error));
      }
    } else {
      // No success or error - something went wrong
      navigate('/accounts');
    }
  }, [searchParams, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center p-8 bg-white rounded-lg shadow-lg">
        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
        <h2 className="text-xl font-semibold mb-2">Processing Authentication...</h2>
        <p className="text-gray-600">Please wait while we complete your authorization.</p>
      </div>
    </div>
  );
}