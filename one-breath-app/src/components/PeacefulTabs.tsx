import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Brain, User, TrendingUp } from "lucide-react";
import QuoteOfTheDay from "./QuoteOfTheDay";
import meditationBg from "@/assets/meditation-silhouette.jpg";

type TabType = "practice" | "progress" | "community" | null;

const PeacefulTabs = () => {
  const [selectedTab, setSelectedTab] = useState<TabType>(null);
  const [isExpanding, setIsExpanding] = useState(false);
  const [animationsComplete, setAnimationsComplete] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimationsComplete(true);
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  const handleTabClick = (tab: TabType) => {
    if (isExpanding) return;
    
    setIsExpanding(true);
    
    // Immediate navigation for responsiveness
    if (tab === "practice") {
      navigate("/practice");
    } else if (tab === "progress") {
      navigate("/progress");
    } else if (tab === "community") {
      navigate("/community");
    }
  };

  const getTabStyles = (tab: TabType) => {
    if (selectedTab && selectedTab !== tab) {
      return "opacity-0 scale-90 pointer-events-none transition-all duration-300";
    }
    if (selectedTab === tab) {
      return "fixed inset-0 z-50 scale-100 opacity-100 transition-all duration-300";
    }
    return "";
  };

  return (
    <div className="fixed inset-0 overflow-hidden">
      {/* Background */}
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${meditationBg})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-black/40" />
      </div>

      {/* Quote of the Day */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-20">
        <QuoteOfTheDay />
      </div>

      {/* Tabs Container */}
      <div 
        className="relative h-full flex items-center justify-center gap-8 px-8"
        style={{ perspective: '1500px', perspectiveOrigin: 'center center' }}
      >
        {/* Practice Tab - Left (Combined Meditate & Yoga) */}
        <div
          onClick={() => handleTabClick("practice")}
          className={`group relative w-80 h-[500px] rounded-3xl overflow-hidden cursor-pointer
            ${getTabStyles("practice")}
            ${selectedTab === null ? "tile-slide-left" : ""}`}
            style={{ 
            animationDelay: '0.05s',
            transformStyle: 'preserve-3d',
            transition: selectedTab 
              ? 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)' 
              : animationsComplete && !selectedTab 
              ? 'transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)' 
              : 'none',
            backfaceVisibility: 'hidden',
            willChange: selectedTab ? 'transform, opacity' : animationsComplete && !selectedTab ? 'transform' : 'auto',
          }}
          onMouseEnter={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(40px) rotateY(-8deg) rotateX(8deg) scale(1.03)';
            }
          }}
          onMouseLeave={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(0) rotateY(0deg) rotateX(0deg) scale(1)';
            }
          }}
        >
          <div 
            className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/85 via-[hsl(var(--gradient-meditation-mid))]/85 to-[hsl(var(--gradient-yoga-end))]/85 rounded-3xl"
            style={{
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)',
              transform: 'translateZ(0)',
              willChange: 'auto',
            }}
          />
          
          <div className="relative h-full flex flex-col items-center justify-center p-8 text-center z-10">
            <Brain className="w-16 h-16 text-white mb-6 grayscale group-hover:grayscale-0 transition-all duration-300 group-hover:scale-110 group-hover:rotate-3" style={{ willChange: 'transform' }} />
            <h2 className="text-4xl font-light text-white mb-4 transition-opacity duration-300 group-hover:opacity-100">Practice</h2>
            <p className="text-white/80 font-light leading-relaxed transition-opacity duration-300 group-hover:opacity-100">
              Meditation and yoga for mindfulness and movement
            </p>
          </div>

          {/* Decorative circles - static */}
          <div className="absolute -top-10 -left-10 w-32 h-32 rounded-full bg-white/10" />
          <div className="absolute -bottom-10 -right-10 w-40 h-40 rounded-full bg-white/10" />
        </div>

        {/* Progress Tab - Center */}
        <div
          onClick={() => handleTabClick("progress")}
          className={`group relative w-80 h-[500px] rounded-3xl overflow-hidden cursor-pointer
            ${getTabStyles("progress")}
            ${selectedTab === null ? "tile-slide-bottom" : ""}`}
            style={{ 
            animationDelay: '0.15s',
            transformStyle: 'preserve-3d',
            transition: selectedTab 
              ? 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)' 
              : animationsComplete && !selectedTab 
              ? 'transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)' 
              : 'none',
            backfaceVisibility: 'hidden',
            willChange: selectedTab ? 'transform, opacity' : animationsComplete && !selectedTab ? 'transform' : 'auto',
          }}
          onMouseEnter={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(40px) rotateX(-8deg) scale(1.03)';
            }
          }}
          onMouseLeave={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(0) rotateX(0deg) scale(1)';
            }
          }}
        >
          <div 
            className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--gradient-yoga-start))]/85 via-[hsl(var(--gradient-yoga-mid))]/85 to-[hsl(var(--gradient-yoga-end))]/85 rounded-3xl"
            style={{
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)',
              transform: 'translateZ(0)',
              willChange: 'auto',
            }}
          />
          
          <div className="relative h-full flex flex-col items-center justify-center p-8 text-center z-10">
            <TrendingUp className="w-16 h-16 text-white mb-6 grayscale group-hover:grayscale-0 transition-all duration-300 group-hover:scale-110 group-hover:rotate-12" style={{ willChange: 'transform' }} />
            <h2 className="text-4xl font-light text-white mb-4 transition-opacity duration-300 group-hover:opacity-100">Progress</h2>
            <p className="text-white/80 font-light leading-relaxed transition-opacity duration-300 group-hover:opacity-100">
              Track your journey with calendar, journal, and stats
            </p>
          </div>

          <div className="absolute top-10 right-10 w-24 h-24 rounded-full bg-white/10" />
          <div className="absolute bottom-10 left-10 w-32 h-32 rounded-full bg-white/10" />
        </div>

        {/* Community Tab - Right */}
        <div
          onClick={() => handleTabClick("community")}
          className={`group relative w-80 h-[500px] rounded-3xl overflow-hidden cursor-pointer
            ${getTabStyles("community")}
            ${selectedTab === null ? "tile-slide-right" : ""}`}
            style={{ 
            animationDelay: '0.25s',
            transformStyle: 'preserve-3d',
            transition: selectedTab 
              ? 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)' 
              : animationsComplete && !selectedTab 
              ? 'transform 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94)' 
              : 'none',
            backfaceVisibility: 'hidden',
            willChange: selectedTab ? 'transform, opacity' : animationsComplete && !selectedTab ? 'transform' : 'auto',
          }}
          onMouseEnter={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(40px) rotateY(8deg) rotateX(8deg) scale(1.03)';
            }
          }}
          onMouseLeave={(e) => {
            if (!selectedTab && animationsComplete) {
              e.currentTarget.style.transform = 'translateZ(0) rotateY(0deg) rotateX(0deg) scale(1)';
            }
          }}
        >
          <div 
            className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--gradient-community-start))]/85 via-[hsl(var(--gradient-community-mid))]/85 to-[hsl(var(--gradient-community-end))]/85 rounded-3xl"
            style={{
              boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)',
              transform: 'translateZ(0)',
              willChange: 'auto',
            }}
          />
          
          <div className="relative h-full flex flex-col items-center justify-center p-8 text-center z-10">
            <User className="w-16 h-16 text-white mb-6 grayscale group-hover:grayscale-0 transition-all duration-300 group-hover:scale-110 group-hover:-rotate-3" style={{ willChange: 'transform' }} />
            <h2 className="text-4xl font-light text-white mb-4 transition-opacity duration-300 group-hover:opacity-100">Community</h2>
            <p className="text-white/80 font-light leading-relaxed transition-opacity duration-300 group-hover:opacity-100">
              Connect with others on their mindfulness journey and share experiences
            </p>
          </div>

          <div className="absolute top-10 left-10 w-36 h-36 rounded-full bg-white/10" />
          <div className="absolute -bottom-10 -right-10 w-28 h-28 rounded-full bg-white/10" />
        </div>
      </div>

      {/* Background decorative circles - static for performance */}
      <div className="absolute top-20 right-20 w-64 h-64 rounded-full bg-white/5" />
      <div className="absolute bottom-20 left-20 w-48 h-48 rounded-full bg-white/5" />
    </div>
  );
};

export default PeacefulTabs;
