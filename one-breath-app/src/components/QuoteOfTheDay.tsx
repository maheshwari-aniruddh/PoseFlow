import { useMemo } from "react";
import quotes from "@/data/quotes.json";

const QuoteOfTheDay = ({ compact = false }: { compact?: boolean }) => {
  const quote = useMemo(() => {
    const now = new Date();
    const dayOfYear = Math.floor(
      (now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 86400000
    );
    const idx = dayOfYear % quotes.length;
    return quotes[idx];
  }, []);

  if (compact) {
    return (
      <div className="rounded-xl px-4 py-3 border border-white/20 max-w-sm bg-white/10 backdrop-blur-md">
        <p className="text-[10px] uppercase tracking-widest text-white/70 font-light mb-1.5">
          Quote of the Day
        </p>
        <p className="text-white text-sm font-light leading-snug italic">
          &ldquo;{quote}&rdquo;
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl px-6 py-5 border border-white/20 w-full max-w-2xl bg-white/10 backdrop-blur-md">
      <p className="text-xs uppercase tracking-widest text-white/70 font-light mb-2">
        Quote of the Day
      </p>
      <p className="text-white text-lg font-light leading-relaxed italic">
        &ldquo;{quote}&rdquo;
      </p>
    </div>
  );
};

export default QuoteOfTheDay;
