import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Controller('health')
export class SystemController {
  constructor(private configService: ConfigService) {}

  @Get()
  getHealth() {
    return {
      status: 'ok',
      service: 'rag-chatbot-api',
      timestamp: new Date().toISOString(),
      workerUrl: this.configService.get<string>('workerUrl') || 'http://localhost:8000',
    };
  }
}
