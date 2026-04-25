/*
CHAT SERVICE
============
WHAT: Handles chat logic — calls Python worker, saves history.
WHY:  All business logic here, controller stays thin.

FLOW:
  1. Get/create chat session
  2. Build chat history from DB (last 5 messages)
  3. Call Python FastAPI worker: POST /chat
  4. Save question + answer to DB
  5. Return answer + sources to controller
*/
import { BadGatewayException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import axios from 'axios';
import { ConfigService } from '@nestjs/config';
import { ChatSession } from './chat-session.entity';
import { ChatMessage } from './chat-message.entity';
import { CreateChatDto } from './dto/create-chat.dto';

@Injectable()
export class ChatService {
  private workerUrl: string;

  constructor(
    @InjectRepository(ChatSession)
    private sessionsRepo: Repository<ChatSession>,
    @InjectRepository(ChatMessage)
    private messagesRepo: Repository<ChatMessage>,
    private configService: ConfigService,
  ) {
    // Python worker URL from config
    this.workerUrl = this.configService.get('workerUrl');
  }

  async chat(userId: string, dto: CreateChatDto) {
    // STEP 1: Get or create session
    let session: ChatSession;

    if (dto.sessionId) {
      session = await this.sessionsRepo.findOne({
        where: { id: dto.sessionId, userId }
      });
      if (!session) throw new NotFoundException('Session not found');
    } else {
      // Create new session
      // Title = first 50 chars of question
      session = await this.sessionsRepo.save({
        userId,
        namespace: dto.namespace || 'default',
        title: dto.question.substring(0, 50),
      });
    }

    // STEP 2: Get chat history from DB (last 5 pairs)
    const recentMessages = await this.messagesRepo.find({
      where: { sessionId: session.id },
      order: { createdAt: 'DESC' },
      take: 10,  // Last 10 messages = 5 pairs
    });

    // Format history for Python worker
    // WHY reverse: DB returns newest first, we need oldest first
    const chatHistory = this._formatHistory(recentMessages.reverse());

    // STEP 3: Call Python FastAPI worker
    let workerResponse;
    try {
      workerResponse = await axios.post(
        `${this.workerUrl}/chat`,
        {
          question: dto.question,
          namespace: dto.namespace || session.namespace,
          chat_history: chatHistory,
          top_k: dto.topK,
        },
        { timeout: 60000 }, // 60s timeout for LLM response
      );
    } catch (error: any) {
      const workerMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        'Worker service unavailable';

      throw new BadGatewayException({
        message: 'Failed to get response from RAG worker',
        workerError: workerMessage,
      });
    }

    const { answer, sources, chunks_used } = workerResponse.data;

    // STEP 4: Save question to DB
    await this.messagesRepo.save({
      sessionId: session.id,
      userId,
      role:      'user',
      content:   dto.question,
    });

    // STEP 5: Save answer to DB
    await this.messagesRepo.save({
      sessionId: session.id,
      userId,
      role:       'assistant',
      content:    answer,
      sources:    sources,
      chunksUsed: chunks_used,
    });

    return {
      sessionId: session.id,
      answer,
      sources,
      chunks_used,
      question: dto.question,
    };
  }

  async getSessions(userId: string) {
    return this.sessionsRepo.find({
      where:  { userId, isActive: true },
      order:  { updatedAt: 'DESC' },
      take:   20,
    });
  }

  async getMessages(userId: string, sessionId: string) {
    // Verify session belongs to user
    const session = await this.sessionsRepo.findOne({
      where: { id: sessionId, userId }
    });
    if (!session) throw new NotFoundException('Session not found');

    return this.messagesRepo.find({
      where: { sessionId },
      order: { createdAt: 'ASC' },
    });
  }

  async deleteSession(userId: string, sessionId: string) {
    const session = await this.sessionsRepo.findOne({
      where: { id: sessionId, userId }
    });
    if (!session) throw new NotFoundException('Session not found');

    await this.sessionsRepo.update(sessionId, { isActive: false });
    return { message: 'Session deleted' };
  }

  private _formatHistory(messages: ChatMessage[]) {
    // Convert DB messages → Python worker format
    // [{question: "...", answer: "..."}]
    const history = [];
    for (let i = 0; i < messages.length - 1; i += 2) {
      const userMsg      = messages[i];
      const assistantMsg = messages[i + 1];
      if (userMsg && assistantMsg) {
        history.push({
          question: userMsg.content,
          answer:   assistantMsg.content,
        });
      }
    }
    return history;
  }
}
