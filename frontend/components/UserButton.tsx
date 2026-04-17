'use client';

import { UserButton as ClerkUserButton } from '@clerk/nextjs';

/**
 * User profile button with dropdown menu
 * Shows user avatar, name, and logout option
 */
export function UserButton() {
  return (
    <ClerkUserButton
      appearance={{
        elements: {
          avatarBox: 'w-10 h-10',
        },
      }}
    />
  );
}
