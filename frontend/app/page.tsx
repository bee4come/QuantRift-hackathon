'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import SearchBar from './components/SearchBar';
import PlayerResults from './components/PlayerResults';
import Header from './components/Header';
import Footer from './components/Footer';
import ProcessingStatus from './components/ProcessingStatus';
import AnnualReport from './components/AnnualReport';
import { SearchProvider, useSearch } from './context/SearchContext';
import { ServerProvider } from './context/ServerContext';

function HomeContent() {
  const { isSearched, clearPlayers } = useSearch();
  const pathname = usePathname();
  
  // Ensure search state is cleared when on home page
  useEffect(() => {
    if (pathname === '/' && isSearched) {
      // Small delay to ensure page has rendered
      setTimeout(() => {
        clearPlayers();
      }, 100);
    }
  }, [pathname, isSearched, clearPlayers]);
  
  return (
    <>
      <div className="min-h-screen flex flex-col relative" style={{ zIndex: 1 }}>
        {/* Header - always at top */}
        <Header />

        {/* Main Content - Search Bar always centered */}
        <div 
          className="flex items-center justify-center w-full"
          style={{
            marginTop: '8rem',
            marginBottom: '4rem',
            minHeight: '400px'
          }}
        >
          <SearchBar isSearched={isSearched} />
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
