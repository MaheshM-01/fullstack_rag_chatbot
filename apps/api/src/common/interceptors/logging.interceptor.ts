/*
LOGGING INTERCEPTOR
===================
WHAT: Logs all incoming requests and their response times.
WHY:  Debugging + monitoring — see which endpoints are slow.
      "POST /chat took 2341ms" → helps identify bottlenecks.
WHERE: Applied globally in main.ts
WHEN:  Every API request
*/
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request   = context.switchToHttp().getRequest();
    const method    = request.method;
    const url       = request.url;
    const startTime = Date.now();

    console.log(`→ ${method} ${url}`);

    return next.handle().pipe(
      tap(() => {
        const duration = Date.now() - startTime;
        console.log(`← ${method} ${url} [${duration}ms]`);
      }),
    );
  }
}