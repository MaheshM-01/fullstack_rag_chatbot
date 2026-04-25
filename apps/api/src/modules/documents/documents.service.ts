import { BadGatewayException, Injectable } from '@nestjs/common';
import axios from 'axios';
import { ConfigService } from '@nestjs/config';
import * as FormData from 'form-data';
import * as fs from 'fs';

@Injectable()
export class DocumentsService {
  private workerUrl: string;

  constructor(private configService: ConfigService) {
    this.workerUrl = this.configService.get<string>('workerUrl') || 'http://localhost:8000';
  }

  async ingestFile(filePath: string, fileName: string, namespace: string = 'default') {
    try {
      const formData = new FormData();
      formData.append('file', fs.createReadStream(filePath), fileName);

      const response = await axios.post(
        `${this.workerUrl}/ingest/file?namespace=${namespace}`,
        formData,
        { headers: formData.getHeaders(), timeout: 120000 },
      );

      return response.data;
    } catch (error: any) {
      const workerMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        'Worker service unavailable';

      throw new BadGatewayException({
        message: 'Failed to ingest file in worker',
        workerError: workerMessage,
      });
    } finally {
      if (filePath && fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    }
  }

  async ingestUrl(url: string, namespace: string = 'default') {
    try {
      const response = await axios.post(
        `${this.workerUrl}/ingest/url`,
        { url, namespace },
        { timeout: 60000 },
      );
      return response.data;
    } catch (error: any) {
      const workerMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        'Worker service unavailable';

      throw new BadGatewayException({
        message: 'Failed to ingest URL in worker',
        workerError: workerMessage,
      });
    }
  }

  async getStats() {
    try {
      const response = await axios.get(`${this.workerUrl}/stats`, { timeout: 30000 });
      return response.data;
    } catch (error: any) {
      const workerMessage =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        'Worker service unavailable';

      throw new BadGatewayException({
        message: 'Failed to fetch worker stats',
        workerError: workerMessage,
      });
    }
  }
}
