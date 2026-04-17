'use client';

import { useAuth as useClerkAuth, useUser } from '@clerk/nextjs';
import { useEffect, useState } from 'react';

/**
 * Client-side authentication hook
 * Provides access to user info, JWT token, and auth state
 */
export function useAuth() {
  const { isLoaded, userId, sessionId, getToken } = useClerkAuth();
  const { user: clerkUser } = useUser();
  const [token, setToken] = useState<string | null>(null);

  // Fetch token on mount and when auth state changes
  useEffect(() => {
    if (userId) {
      getToken().then((t) => setToken(t || null));
    } else {
      setToken(null);
    }
  }, [userId, getToken]);

  // Get company ID from user metadata
  const companyId = clerkUser?.organizationMemberships?.[0]?.organization?.id || 'default';

  return {
    isLoaded,
    isAuthenticated: !!userId,
    userId,
    sessionId,
    token,
    user: clerkUser ? {
      id: clerkUser.id,
      email: clerkUser.primaryEmailAddress?.emailAddress,
      companyId,
    } : null,
    
    /**
     * Get JWT token for API requests
     * This token includes user_id and company_id claims
     */
    getToken: async () => {
      return getToken();
    },
    
    /**
     * Get company ID from user metadata
     * In production, this should come from organization membership
     */
    getCompanyId: () => {
      return companyId;
    },
  };
}
