# Plan for Development Automatic Login System

This document outlines the plan to implement a secure, development-only automatic login system. This system will streamline the development process for agents by bypassing the need for manual Google login in environments where the primary developer's account isn't available.

## 1. Backend: Create a development-only login endpoint

- **Action:** Add a new endpoint, `/api/v1/auth/dev/login`, to `api/auth.py`.
- **Details:**
    - This endpoint will only be active when the `SELEXTRACT_ENVIRONMENT` environment variable is set to 'development'.
    - It will find or create a user with the email `yunusemremre@gmail.com`.
    - It will generate a JWT token for this user and return it.

## 2. Backend: Secure the development endpoint

- **Action:** Ensure the `/api/v1/auth/dev/login` endpoint is properly secured.
- **Details:**
    - The endpoint must return a 404 Not Found or 403 Forbidden error if the `SELEXTRACT_ENVIRONMENT` is not 'development'. This is a critical security measure to prevent exposure in production.

## 3. Frontend: Implement automatic login logic

- **Action:** Modify the frontend to support automatic login.
- **Details:**
    - In `frontend/lib/auth.tsx`, create a new function to call the `/api/v1/auth/dev/login` endpoint.
    - Modify the `AuthProvider` component to check for a new environment variable, `NEXT_PUBLIC_DEV_AUTO_LOGIN`.
    - If `NEXT_PUBLIC_DEV_AUTO_LOGIN` is set to `true`, the application will automatically call the new development login endpoint on startup.

## 4. Configuration: Update environment files

- **Action:** Add the necessary environment variables to enable the feature.
- **Details:**
    - Add `DEV_AUTO_LOGIN=true` to the root `.env.dev` file.
    - Ensure `NEXT_PUBLIC_DEV_AUTO_LOGIN=true` is loaded as a frontend environment variable from the root `.env.dev` file. This will enable the feature by default in the standard development environment.

## 5. Documentation: Create a new markdown file

- **Action:** Document the new automatic login feature.
- **Details:**
    - Create a new file, `docs/DEVELOPMENT_AUTO_LOGIN.md`.
    - The documentation will explain how the feature works, how to enable or disable it, and the security considerations involved.

This plan provides a seamless and secure way to accelerate development by removing the friction of manual login, while maintaining a strong security posture by isolating the feature to the development environment.