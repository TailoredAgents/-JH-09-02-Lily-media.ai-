/**
 * DEPRECATED: This file has been replaced by SecureAuthContext.jsx
 * 
 * This implementation used localStorage for access tokens which is vulnerable to XSS attacks.
 * 
 * P0-13a Security Fix: Access tokens moved to memory-only storage
 * Refresh tokens moved to HTTP-only cookies
 * 
 * Migration completed: All components now use SecureAuthContext.jsx
 * 
 * This file is kept for reference but should not be imported or used.
 * It will be removed in a future cleanup.
 * 
 * See: docs/secure-auth-migration.md for migration details
 */

// This file is deprecated and should not be used
throw new Error('DEPRECATED: Use SecureAuthContext.jsx instead of AuthContext.jsx for security (P0-13a)')

export const useAuth = () => {
  throw new Error('DEPRECATED: Import useAuth from SecureAuthContext.jsx instead')
}

export const AuthProvider = () => {
  throw new Error('DEPRECATED: Import AuthProvider from SecureAuthContext.jsx instead')
}