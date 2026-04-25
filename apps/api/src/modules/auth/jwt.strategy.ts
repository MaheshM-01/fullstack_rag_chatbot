/*
JWT STRATEGY
============
WHAT: Passport strategy that validates JWT tokens.
WHY:  JwtAuthGuard uses this to verify "Authorization: Bearer <token>"
HOW:
  1. Extract token from Authorization header
  2. Verify signature using JWT_SECRET
  3. Decode payload → { sub: userId, email: "..." }
  4. Call validate() → return user object
  5. NestJS attaches user to request.user
  
  In controllers: @Req() req → req.user.id
*/
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { UsersService } from '../users/users.service';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(
    private configService: ConfigService,
    private usersService: UsersService,
  ) {
    super({
      // Extract token from "Authorization: Bearer <token>" header
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      // Reject expired tokens
      ignoreExpiration: false,
      // Secret key to verify token signature
      secretOrKey: configService.get('jwt.secret'),
    });
  }

  async validate(payload: { sub: string; email: string }) {
    // payload = decoded JWT content
    // sub = user ID (standard JWT claim)
    const user = await this.usersService.findById(payload.sub);
    if (!user || !user.isActive) {
      throw new UnauthorizedException('User not found or inactive');
    }
    // Return value attached to request.user in all guards/controllers
    return { id: user.id, email: user.email, role: user.role };
  }
}