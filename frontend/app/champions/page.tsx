import ChampionsClient from './ChampionsClient';
import { ServerProvider } from '../context/ServerContext';
import { SearchProvider } from '../context/SearchContext';

export default function ChampionsPage() {
  return (
    <ServerProvider>
      <SearchProvider>
        <ChampionsClient />
      </SearchProvider>
    </ServerProvider>
  );
}
