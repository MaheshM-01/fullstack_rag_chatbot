/*
HTTP EXCEPTION FILTER
=====================
WHAT: Global error handler — catches all unhandled exceptions.
WHY:  Without this, errors return ugly HTML stack traces.
      With this, ALL errors return clean JSON:
      { statusCode: 404, message: "Not found", timestamp: "..." }
WHERE: Applied globally in main.ts
WHEN:  Any endpoint throws an error
*/
import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { Request, Response } from 'express';

@Catch()  // @Catch() with no args = catch EVERYTHING
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx      = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request  = ctx.getRequest<Request>();

    // Determine status code
    // HttpException → use its status
    // Unknown error → 500 Internal Server Error
    const status =
      exception instanceof HttpException
        ? exception.getStatus()
        : HttpStatus.INTERNAL_SERVER_ERROR;

    // Get error message
    const message =
      exception instanceof HttpException
        ? exception.getResponse()
        : 'Internal server error';

    // Return clean JSON error response
    response.status(status).json({
      statusCode: status,
      timestamp:  new Date().toISOString(),
      path:       request.url,
      message:    typeof message === 'object' ? message : { error: message },
    });
  }
}