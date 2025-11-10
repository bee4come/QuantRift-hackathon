import { Metadata } from 'next';
import ShareReportView from './ShareReportView';

// Helper function to extract first paragraph from markdown
function extractFirstParagraph(markdown: string): string {
  const lines = markdown.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('*') && !trimmed.startsWith('-')) {
      return trimmed.substring(0, 160);
    }
  }
  return 'League of Legends AI Analysis Report';
}

export async function generateMetadata({ params }: {
  params: Promise<{ shareId: string }>
}): Promise<Metadata> {
  try {
    const { shareId } = await params;

    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/share/${shareId}`, {
      cache: 'no-store'
    });

    if (!response.ok) {
      return {
        title: 'Report Not Found | QuantRift',
        description: 'This report could not be found.'
      };
    }

    const data = await response.json();

    const title = `${data.player.gameName}'s ${data.agent_type} | QuantRift`;
    const description = extractFirstParagraph(data.report_content);
    const url = `${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/share/${shareId}`;

    return {
      title,
      description,
      openGraph: {
        title,
        description,
        type: 'article',
        url,
        siteName: 'QuantRift',
        images: [{
          url: '/og-image.png', // Static OG image
          width: 1200,
          height: 630,
          alt: title
        }]
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
        images: ['/og-image.png']
      }
    };
  } catch (error) {
    console.error('Error generating metadata:', error);
    return {
      title: 'QuantRift Analysis Report',
      description: 'League of Legends AI Analysis'
    };
  }
}

export default async function SharePage({ params }: {
  params: Promise<{ shareId: string }>
}) {
  const { shareId } = await params;

  return <ShareReportView shareId={shareId} />;
}
