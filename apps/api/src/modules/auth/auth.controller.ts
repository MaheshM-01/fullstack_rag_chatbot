/*
AUTH CONTROLLER
===============
WHAT: HTTP endpoints for authentication.
WHY:  Thin layer — just receives HTTP request, calls service, returns response.
      NO business logic here — that's in auth.service.ts
*/
import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AuthService } from './auth.service';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';

@Controller('auth')  // Base path: /auth
export class AuthController {
  constructor(private authService: AuthService) {}

  @Post('register')  // POST /auth/register
  async register(@Body() dto: RegisterDto) {
    return this.authService.register(dto);
  }

  @Post('login')     // POST /auth/login
  @HttpCode(HttpStatus.OK)  // Return 200 not 201 for login
  async login(@Body() dto: LoginDto) {
    return this.authService.login(dto);
  }
}