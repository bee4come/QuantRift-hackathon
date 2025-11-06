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

  // Decode URI components in case they come encoded from the URL
  const decodedGameName = decodeURIComponent(gameName);
  const decodedTagLine = decodeURIComponent(tagLine);

  return (
    <ServerProvider>
      <SearchProvider>
        <PlayerProfileClient gameName={decodedGameName} tagLine={decodedTagLine} />
      </SearchProvider>
    </ServerProvider>
  );
}

