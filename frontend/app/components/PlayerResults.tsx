'use client';

import React from 'react';
import { motion } from 'framer-motion';
import PlayerCard from './PlayerCard';
import { useSearch } from '../context/SearchContext';

export default function PlayerResults() {
  const { searchedPlayers } = useSearch();

  if (searchedPlayers.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3, duration: 0.5 }}
      className="w-full max-w-7xl mx-auto px-4 mt-12 pb-12"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {searchedPlayers.map((player, index) => (
          <PlayerCard key={player.username} player={player} index={index} />
        ))}
      </div>
    </motion.div>
  );
}

