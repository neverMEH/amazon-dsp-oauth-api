# Spec Tasks

## Tasks

- [ ] 1. Fix Account Details Display and Functionality
  - [ ] 1.1 Write tests for AccountDetailsModal component
  - [ ] 1.2 Fix account data mapping in AccountManagementPage to properly pass account information
  - [ ] 1.3 Update Account type interface to match backend response structure
  - [ ] 1.4 Ensure AccountCard displays correct account name, ID, and type
  - [ ] 1.5 Verify all account cards show proper marketplace and status information
  - [ ] 1.6 Run tests to ensure all account display tests pass

- [ ] 2. Fix Details Button Functionality
  - [ ] 2.1 Write tests for Details button click handler
  - [ ] 2.2 Debug AccountDetailsModal opening mechanism
  - [ ] 2.3 Ensure modal receives correct account data when opened
  - [ ] 2.4 Verify modal displays all account information correctly
  - [ ] 2.5 Test modal close functionality
  - [ ] 2.6 Verify all modal interaction tests pass

- [ ] 3. Update Status Counters
  - [ ] 3.1 Write tests for status counter calculations
  - [ ] 3.2 Fix getStatusCounts function to properly count account statuses
  - [ ] 3.3 Update account status determination logic based on token expiration
  - [ ] 3.4 Ensure status counters reflect real-time account data
  - [ ] 3.5 Verify status counter updates when accounts are synced
  - [ ] 3.6 Run tests to ensure status counter logic is correct

- [ ] 4. Fix Account Data Synchronization
  - [ ] 4.1 Write tests for account sync functionality
  - [ ] 4.2 Debug getAccounts API call and response handling
  - [ ] 4.3 Fix data transformation between backend and frontend formats
  - [ ] 4.4 Ensure account metadata (alternate IDs, country codes) is preserved
  - [ ] 4.5 Verify token expiration status is correctly determined
  - [ ] 4.6 Test complete sync flow from API to UI

- [ ] 5. Integration Testing and Verification
  - [ ] 5.1 Test complete account management page functionality
  - [ ] 5.2 Verify all 6 disconnected accounts display correctly
  - [ ] 5.3 Test "Sync from Amazon" button functionality
  - [ ] 5.4 Verify account re-authorization flow
  - [ ] 5.5 Test account disconnection functionality
  - [ ] 5.6 Ensure all integration tests pass successfully