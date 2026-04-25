/*
VALIDATION PIPE
===============
WHAT: Validates incoming request data against DTO class rules.
WHY:  class-validator decorators (@IsEmail, @MinLength etc.)
      only work when ValidationPipe is applied.
      Without pipe → decorators are ignored!
WHERE: Applied globally in main.ts
*/
import { ValidationPipe } from '@nestjs/common';

// Export configured ValidationPipe instance
// WHY configured:
//   whitelist:true → strip unknown fields (security)
//   forbidNonWhitelisted:true → error on unknown fields
//   transform:true → auto-convert types (string "5" → number 5)
export const globalValidationPipe = new ValidationPipe({
  whitelist:            true,
  forbidNonWhitelisted: true,
  transform:            true,
});