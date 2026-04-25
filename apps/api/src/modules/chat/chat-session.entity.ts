/*
CHAT SESSION ENTITY
===================
WHAT: One chat session = one conversation thread.
WHY:  Store chat history in DB so user can see past conversations.
*/
import {
  Entity, Column, PrimaryGeneratedColumn,
  CreateDateColumn, UpdateDateColumn, ManyToOne, OneToMany
} from 'typeorm';
import { User } from '../users/user.entity';

@Entity('chat_sessions')
export class ChatSession {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  userId: string;

  @Column({ nullable: true })
  title: string;  // Auto-generated from first question

  @Column({ default: 'default' })
  namespace: string;  // Which docs this session uses

  @Column({ default: true })
  isActive: boolean;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}