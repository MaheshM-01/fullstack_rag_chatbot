/*
USERS SERVICE
=============
WHAT: Database operations for users table.
WHY:  AuthService needs to find/create users.
      All DB logic here, not in controllers.
*/
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';
import * as bcrypt from 'bcryptjs';

@Injectable()
export class UsersService {
  constructor(
    // TypeORM injects repository for User entity
    // WHY @InjectRepository: NestJS DI system needs this decorator
    @InjectRepository(User)
    private usersRepository: Repository<User>,
  ) {}

  async findByEmail(email: string): Promise<User | null> {
    // Find user by email (used in login)
    return this.usersRepository.findOne({ where: { email } });
  }

  async findById(id: string): Promise<User | null> {
    // Find user by ID (used in JWT verification)
    return this.usersRepository.findOne({ where: { id } });
  }

  async create(email: string, password: string, name?: string): Promise<User> {
    // Hash password before saving
    // WHY bcrypt: One-way hash — even DB admin can't see real password
    // saltRounds=10: Higher = slower but more secure. 10 is standard.
    const hashedPassword = await bcrypt.hash(password, 10);

    const user = this.usersRepository.create({
      email,
      password: hashedPassword,
      name: name || email.split('@')[0],
    });

    return this.usersRepository.save(user);
  }

  async validatePassword(plainPassword: string, hashedPassword: string): Promise<boolean> {
    // Compare plain password against stored hash
    // bcrypt.compare handles the salt automatically
    return bcrypt.compare(plainPassword, hashedPassword);
  }
}