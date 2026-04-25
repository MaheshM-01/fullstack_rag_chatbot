import { IsOptional, IsString, IsUrl, MaxLength } from 'class-validator';

export class IngestUrlDto {
  @IsUrl({}, { message: 'Please provide a valid URL' })
  url: string;

  @IsString()
  @IsOptional()
  @MaxLength(100)
  namespace?: string;
}
