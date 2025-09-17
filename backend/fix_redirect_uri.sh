#!/bin/bash

echo "Updating redirect URI to use 127.0.0.1 instead of localhost..."

# Update .env file
sed -i 's|http://localhost:8000|http://127.0.0.1:8000|g' ../.env

echo "Updated .env file. New redirect URI: http://127.0.0.1:8000/api/v1/auth/amazon/callback"
echo ""
echo "⚠️  IMPORTANT: You must also update this in your Amazon Developer Console!"
echo "1. Log into Amazon Developer Console"
echo "2. Go to your app settings"
echo "3. Update redirect URI to: http://127.0.0.1:8000/api/v1/auth/amazon/callback"
echo "4. Save changes"
echo "5. Restart your backend server"