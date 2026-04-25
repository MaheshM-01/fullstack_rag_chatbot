import { IsOptional, IsString, MaxLength } from 'class-validator';

export class UploadDocumentDto {
  @IsString()
  @IsOptional()
  @MaxLength(100)
  namespace?: string;
}
