export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30 seconds
};

export const CHARACTERS = {
  karan: { name: 'Karan Mehta', role: 'CFO' },
  neha: { name: 'Neha Singh', role: 'COO' },
  arjun: { name: 'Arjun Sharma', role: 'Head of Legal' },
  raghav: { name: 'Raghav Patel', role: 'VP of Marketplace' },
} as const;
