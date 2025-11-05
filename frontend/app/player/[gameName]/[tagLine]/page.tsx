import PlayerProfileClient from './PlayerProfileClient';
import { ServerProvider } from '@/app/context/ServerContext';
import { SearchProvider } from '@/app/context/SearchContext';

interface PageProps {
  params: Promise<{
    gameName: string;
    tagLine: string;
  }>;
}

export default async function PlayerProfilePage({ params }: PageProps) {
  const { gameName, tagLine } = await params;

  return (
    <ServerProvider>
      <SearchProvider>
        <PlayerProfileClient gameName={gameName} tagLine={tagLine} />
      </SearchProvider>
    </ServerProvider>
  );
}

