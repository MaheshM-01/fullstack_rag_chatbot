/*
USER ENTITY
===========
WHAT: TypeORM entity = database table definition.
      Each property = one column in 'users' table.
WHY:  TypeORM creates/manages the table automatically.
      No manual SQL needed!
WHERE: Used by UsersService for DB operations.
*/
import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  OneToMany,
} from 'typeorm';

@Entity('users')  // Table name in PostgreSQL
export class User {
  @PrimaryGeneratedColumn('uuid')
  // WHY uuid: More secure than sequential integers
  // uuid = "550e8400-e29b-41d4-a716-446655440000" (hard to guess)
  id: string;

  @Column({ unique: true })
  // unique:true → two users can't have same email
  email: string;

  @Column()
  // WHY not store plain password: Security!
  // Always store bcrypt hash: "$2b$10$..." 
  password: string;  // Stored as bcrypt hash

  @Column({ nullable: true })
  name: string;

  @Column({ default: 'user' })
  // Role-based access: 'user' or 'admin'
  role: string;

  @Column({ default: true })
  isActive: boolean;

  @CreateDateColumn()
  // Auto-set when record created
  createdAt: Date;

  @UpdateDateColumn()
  // Auto-updated when record modified
  updatedAt: Date;
}