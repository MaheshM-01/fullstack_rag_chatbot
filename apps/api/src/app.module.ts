/*
APP MODULE
==========
WHAT: Root module — imports ALL other modules.
WHY:  NestJS uses module system to organize code.
      AppModule is the entry point that wires everything together.
*/
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import configuration from './config/configuration';
import { AuthModule } from './modules/auth/auth.module';
import { UsersModule } from './modules/users/users.module';
import { ChatModule } from './modules/chat/chat.module';
import { DocumentsModule } from './modules/documents/documents.module';
import { SystemModule } from './modules/system/system.module';
import { User } from './modules/users/user.entity';
import { ChatSession } from './modules/chat/chat-session.entity';
import { ChatMessage } from './modules/chat/chat-message.entity';

@Module({
  imports: [
    // Config — loads .env, available everywhere
    ConfigModule.forRoot({
      isGlobal: true,        // No need to import in every module
      load:     [configuration],
    }),

    // Database — TypeORM with PostgreSQL
    TypeOrmModule.forRootAsync({
      inject:     [ConfigService],
      useFactory: (config: ConfigService) => ({
        type:        'postgres',
        host:        config.get('database.host'),
        port:        config.get('database.port'),
        username:    config.get('database.user'),
        password:    config.get('database.password'),
        database:    config.get('database.name'),
        entities:    [User, ChatSession, ChatMessage],
        synchronize: true,  // Auto-create tables in development
        // WARNING: synchronize:true is for DEV only!
        // In production: use migrations instead
        logging: false,
      }),
    }),

    // Feature modules
    AuthModule,
    UsersModule,
    ChatModule,
    DocumentsModule,
    SystemModule,
  ],
})
export class AppModule {}
