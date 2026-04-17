import { auth } from '@clerk/nextjs/server';

/**
 * Get the current user's authentication token
 * This token contains user_id and company_id claims
 */
export async function getAuthToken(): Promise<string | null> {
  const { getToken } = await auth();
  return getToken();
}

/**
 * Get the current user's session claims
 * Returns user_id and company_id for multi-tenant isolation
 */
export async function getSessionClaims() {
  const { sessionClaims } = await auth();
  
  return {
    userId: sessionClaims?.sub as string | undefined,
    companyId: sessionClaims?.org_id as string | undefined,
  };
}

/**
 * Check if the user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const { userId } = await auth();
  return !!userId;
}
