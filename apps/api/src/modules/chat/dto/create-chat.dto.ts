import { IsString, MinLength, IsOptional, IsInt, Min, Max } from 'class-validator';

export class CreateChatDto {
  @IsString()
  @MinLength(1)
  question: string;

  @IsString()
  @IsOptional()
  sessionId?: string;

  @IsString()
  @IsOptional()
  namespace?: string;

  @IsInt()
  @IsOptional()
  @Min(1)
  @Max(20)
  topK?: number;
}