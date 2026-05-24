import type { Metadata } from 'next';
import { Source_Serif_4, IBM_Plex_Mono } from 'next/font/google';
import { GeistSans } from 'geist/font/sans';
import './globals.css';

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
  display: 'swap',
  variable: '--font-source-serif',
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-ibm-plex-mono',
});

export const metadata: Metadata = {
  title: 'DeltaSci — auditable hypothesis review',
  description:
    'Review surface for DeltaSci co-reasoning runs. Every claim, every knowledge gap, every novel synthesis — visible and inspectable.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sourceSerif.variable} ${ibmPlexMono.variable} ${GeistSans.variable}`}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning on <body> handles attributes injected by
          browser extensions (Grammarly, dark-mode, password managers) after
          server render but before React hydrates. Component-tree mismatches
          still surface normally — this only affects the <body> element. */}
      <body className="font-sans" suppressHydrationWarning>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
