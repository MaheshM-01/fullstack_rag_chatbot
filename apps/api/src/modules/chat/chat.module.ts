import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigModule } from '@nestjs/config';
import { ChatService } from './chat.service';
import { ChatController } from './chat.controller';
import { ChatSession } from './chat-session.entity';
import { ChatMessage } from './chat-message.entity';

@Module({
  imports: [
    TypeOrmModule.forFeature([ChatSession, ChatMessage]),
    ConfigModule,
  ],
  controllers: [ChatController],
  providers:   [ChatService],
})
export class ChatModule {}