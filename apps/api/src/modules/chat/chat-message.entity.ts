/*
CHAT MESSAGE ENTITY
===================
WHAT: Individual message in a chat session.
      Stores both user questions and AI answers.
*/
import {
  Entity, Column, PrimaryGeneratedColumn, CreateDateColumn
} from 'typeorm';

@Entity('chat_messages')
export class ChatMessage {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  sessionId: string;

  @Column()
  userId: string;

  // 'user' = human question, 'assistant' = AI answer
  @Column({ type: 'enum', enum: ['user', 'assistant'] })
  role: 'user' | 'assistant';

  @Column('text')
  content: string;

  @Column({ nullable: true, type: 'jsonb' })
  // Store sources as JSON: [{file, page, score}]
  // jsonb = PostgreSQL binary JSON (faster queries)
  sources: object[];

  @Column({ nullable: true })
  chunksUsed: number;

  @CreateDateColumn()
  createdAt: Date;
}