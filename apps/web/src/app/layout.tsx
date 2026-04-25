import type { Metadata } from 'next';
import { Space_Grotesk, Spectral } from 'next/font/google';
import './globals.css';

const headingFont = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-heading',
  weight: ['400', '500', '700'],
});

const bodyFont = Spectral({
  subsets: ['latin'],
  variable: '--font-body',
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: 'RAG Portfolio Chatbot',
  description: 'End-to-end RAG chatbot using Groq, NestJS, FastAPI, and Next.js.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${headingFont.variable} ${bodyFont.variable}`}>{children}</body>
    </html>
  );
}
