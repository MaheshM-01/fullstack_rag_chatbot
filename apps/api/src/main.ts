import { NestFactory } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';
import { LoggingInterceptor } from './common/interceptors/logging.interceptor';
import { globalValidationPipe } from './common/pipes/validation.pipe';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);
  const port = configService.get<number>('port') || 3001;

  app.enableCors({
    origin: configService.get('frontend.url'),
    credentials: true,
  });

  app.setGlobalPrefix('api');
  app.useGlobalFilters(new HttpExceptionFilter());
  app.useGlobalPipes(globalValidationPipe);
  app.useGlobalInterceptors(new LoggingInterceptor());

  await app.listen(port);

  console.log(`\nNestJS API running at: http://localhost:${port}`);
  console.log(`Health:    GET  http://localhost:${port}/api/health`);
  console.log(`Auth:      POST http://localhost:${port}/api/auth/register`);
  console.log(`Chat:      POST http://localhost:${port}/api/chat`);
  console.log(`Documents: POST http://localhost:${port}/api/documents/upload\n`);
}

bootstrap();
