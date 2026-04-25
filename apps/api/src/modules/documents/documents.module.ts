import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { DocumentsService } from './documents.service';
import { DocumentsController } from './documents.controller';

@Module({
  imports:     [ConfigModule],
  controllers: [DocumentsController],
  providers:   [DocumentsService],
})
export class DocumentsModule {}