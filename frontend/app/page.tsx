'use client';

import SearchBar from './components/SearchBar';
import PlayerResults from './components/PlayerResults';
import DynamicBackground from './components/DynamicBackground';
import Header from './components/Header';
import Footer from './components/Footer';
import ProcessingStatus from './components/ProcessingStatus';
import AnnualReport from './components/AnnualReport';
import EsportsAnnouncements from './components/EsportsAnnouncements';
import { SearchProvider, useSearch } from './context/SearchContext';
import { ServerProvider } from './context/ServerContext';

function HomeContent() {
  return (
    <>
      <DynamicBackground />
      <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
        {/* Header - always at top */}
        <Header />

        {/* Main Content - Search Bar always centered */}
        <div className="flex-1 flex items-center justify-center">
          <SearchBar isSearched={false} />
        </div>

        {/* Footer */}
        <Footer />
      </div>
    </>
  );
}

export default function Home() {
  return (
    <ServerProvider>
      <SearchProvider>
        <HomeContent />
      </SearchProvider>
    </ServerProvider>
  );
}
