'use client';

import { useAdaptiveColors } from '../hooks/useAdaptiveColors';

export default function Footer() {
  const colors = useAdaptiveColors();

  return (
    <footer className="w-full py-6 px-4 mt-auto">
      <div className="max-w-7xl mx-auto">
        {/* Developers and Copyright */}
        <div className="text-center">
          <div className="flex justify-center items-center gap-4">
            <a
              href="https://github.com/uzerone"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium hover:opacity-80 transition-opacity duration-300"
              style={{ color: colors.textPrimary }}
            >
              uzerone
            </a>
            <a
              href="https://github.com/bee4come"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium hover:opacity-80 transition-opacity duration-300"
              style={{ color: colors.textPrimary }}
            >
              bee4come
            </a>
            <span 
              className="text-sm"
              style={{ color: colors.textSecondary }}
            >
              © 2025 QuantRift. All rights reserved.
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
