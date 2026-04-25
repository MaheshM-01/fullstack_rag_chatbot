/*
CHAT CONTROLLER
===============
WHAT: HTTP endpoints for chat operations.
WHY:  Thin controller — just validates, calls service, returns response.
*/
import {
  Controller, Post, Get, Delete,
  Body, Param, Req, UseGuards,
} from '@nestjs/common';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { ChatService } from './chat.service';
import { CreateChatDto } from './dto/create-chat.dto';

@Controller('chat')
@UseGuards(JwtAuthGuard)  // ALL chat routes require JWT token
export class ChatController {
  constructor(private chatService: ChatService) {}

  @Post()  // POST /chat
  async chat(@Req() req, @Body() dto: CreateChatDto) {
    // req.user.id = from JWT token (set by JwtStrategy)
    return this.chatService.chat(req.user.id, dto);
  }

  @Get('sessions')  // GET /chat/sessions
  async getSessions(@Req() req) {
    return this.chatService.getSessions(req.user.id);
  }

  @Get('sessions/:id/messages')  // GET /chat/sessions/:id/messages
  async getMessages(@Req() req, @Param('id') sessionId: string) {
    return this.chatService.getMessages(req.user.id, sessionId);
  }

  @Delete('sessions/:id')  // DELETE /chat/sessions/:id
  async deleteSession(@Req() req, @Param('id') sessionId: string) {
    return this.chatService.deleteSession(req.user.id, sessionId);
  }
}