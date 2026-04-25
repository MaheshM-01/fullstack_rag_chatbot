/*
AUTH SERVICE
============
WHAT: Handles login, register, token generation.
WHY:  Business logic separated from controller (HTTP layer).
*/
import {
  Injectable,
  UnauthorizedException,
  ConflictException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { UsersService } from '../users/users.service';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService:   JwtService,
  ) {}

  async register(dto: RegisterDto) {
    // Check if email already exists
    const existing = await this.usersService.findByEmail(dto.email);
    if (existing) {
      throw new ConflictException('Email already registered');
    }

    // Create user (password hashed inside usersService.create)
    const user = await this.usersService.create(
      dto.email,
      dto.password,
      dto.name,
    );

    // Generate JWT token
    const token = this._generateToken(user.id, user.email);

    return {
      message: 'Registration successful',
      token,
      user: { id: user.id, email: user.email, name: user.name },
    };
  }

  async login(dto: LoginDto) {
    // Find user by email
    const user = await this.usersService.findByEmail(dto.email);
    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }

    // Verify password
    const isValid = await this.usersService.validatePassword(
      dto.password,
      user.password,
    );
    if (!isValid) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = this._generateToken(user.id, user.email);

    return {
      message: 'Login successful',
      token,
      user: { id: user.id, email: user.email, name: user.name },
    };
  }

  private _generateToken(userId: string, email: string): string {
    // JWT payload
    // sub = subject (standard JWT claim for user ID)
    const payload = { sub: userId, email };
    return this.jwtService.sign(payload);
  }
}