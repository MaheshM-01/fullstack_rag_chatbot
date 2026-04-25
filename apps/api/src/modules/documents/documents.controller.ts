import {
  BadRequestException,
  Body,
  Controller,
  Get,
  Post,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import { extname } from 'path';
import { JwtAuthGuard } from '../../common/guards/jwt-auth.guard';
import { DocumentsService } from './documents.service';
import { IngestUrlDto } from './dto/ingest-url.dto';
import { UploadDocumentDto } from './dto/upload-document.dto';

const ALLOWED_EXTENSIONS = new Set(['.pdf', '.txt', '.docx', '.doc']);

@Controller('documents')
@UseGuards(JwtAuthGuard)
export class DocumentsController {
  constructor(private documentsService: DocumentsService) {}

  @Post('upload')
  @UseInterceptors(
    FileInterceptor('file', {
      storage: diskStorage({
        destination: './uploads',
        filename: (req, file, cb) => {
          const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
          cb(null, uniqueSuffix + extname(file.originalname));
        },
      }),
      limits: { fileSize: 10 * 1024 * 1024 },
    }),
  )
  async uploadFile(
    @UploadedFile() file: Express.Multer.File,
    @Body() dto: UploadDocumentDto,
  ) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    const extension = extname(file.originalname).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      throw new BadRequestException(
        `Unsupported file type '${extension}'. Allowed: ${Array.from(ALLOWED_EXTENSIONS).join(', ')}`,
      );
    }

    return this.documentsService.ingestFile(
      file.path,
      file.originalname,
      dto.namespace || 'default',
    );
  }

  @Post('url')
  async ingestUrl(@Body() dto: IngestUrlDto) {
    return this.documentsService.ingestUrl(dto.url, dto.namespace || 'default');
  }

  @Get('stats')
  async getStats() {
    return this.documentsService.getStats();
  }
}
