/*
CONFIGURATION
=============
WHAT: Reads environment variables and exports as typed config object.
WHY:  NestJS @nestjs/config uses this to provide config app-wide.
      Type-safe access vs raw process.env strings.
WHERE: Imported by AppModule, used everywhere via ConfigService.
*/
export default () => ({
  port: parseInt(process.env.API_PORT || '3001', 10),
  
  database: {
    host:     process.env.DB_HOST     || 'localhost',
    port:     parseInt(process.env.DB_PORT || '5432', 10),
    name:     process.env.DB_NAME     || 'ragchatbot',
    user:     process.env.DB_USER     || 'postgres',
    password: process.env.DB_PASSWORD || 'password',
  },
  
  jwt: {
    secret:    process.env.JWT_SECRET     || 'change-this-secret',
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },
  
  // Python RAG worker URL
  // WHY: NestJS calls FastAPI at this URL for RAG operations
  workerUrl: process.env.WORKER_URL || 'http://localhost:8000',
  
  frontend: {
    url: process.env.FRONTEND_URL || 'http://localhost:3000',
  },
});