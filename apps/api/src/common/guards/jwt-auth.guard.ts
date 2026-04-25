/*
JWT AUTH GUARD
==============
WHAT: Protects API endpoints — requires valid JWT token.
WHY:  Without guard, anyone can access /chat, /documents etc.
      With guard, must have valid token (logged-in user only).
HOW:  Reads "Authorization: Bearer <token>" header
      Verifies token with JWT_SECRET
      If valid → allow request
      If invalid → 401 Unauthorized
WHERE: Applied to protected routes with @UseGuards(JwtAuthGuard)
*/
import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  // Extends passport's JWT strategy guard
  // All verification logic in jwt.strategy.ts
}