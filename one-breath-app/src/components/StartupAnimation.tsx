import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import meditationBg from "@/assets/meditation-silhouette.jpg";

const StartupAnimation = () => {
  const navigate = useNavigate();
  const [isLoaded, setIsLoaded] = useState(false);
  const [showButton, setShowButton] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
    const buttonTimer = setTimeout(() => {
      setShowButton(true);
    }, 2000);

    return () => clearTimeout(buttonTimer);
  }, []);

  return (
    <div className="min-h-screen relative">
      {/* Background Image - Fixed for scroll effect */}
      <div 
        className="fixed inset-0 bg-cover bg-center -z-10"
        style={{
          backgroundImage: `url(${meditationBg})`,
          transform: isLoaded ? 'scale(1)' : 'scale(1.08)',
          opacity: isLoaded ? 1 : 0,
          transition: 'transform 2500ms cubic-bezier(0.16, 1, 0.3, 1), opacity 1800ms cubic-bezier(0.16, 1, 0.3, 1)',
          willChange: isLoaded ? 'auto' : 'transform, opacity',
        }}
      >
        {/* Gradient Overlay with animation */}
        <div 
          className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/30 to-black/20 animate-gradient-shift"
          style={{
            opacity: isLoaded ? 1 : 0,
            transition: 'opacity 2000ms cubic-bezier(0.16, 1, 0.3, 1)',
            background: 'linear-gradient(135deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0.2) 100%)',
            backgroundSize: '200% 200%',
          }}
        />
      </div>

      {/* Hero Section */}
      <div 
        className="min-h-screen flex items-center justify-center px-8"
        style={{
          opacity: isLoaded ? 1 : 0,
          transform: isLoaded ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.98)',
          transition: 'opacity 1200ms cubic-bezier(0.16, 1, 0.3, 1) 300ms, transform 1200ms cubic-bezier(0.16, 1, 0.3, 1) 300ms',
          willChange: isLoaded ? 'auto' : 'opacity, transform',
        }}
      >
        <div className="text-center">
          <h1 
            className="text-8xl md:text-9xl font-light text-white mb-6 tracking-wider drop-shadow-2xl animate-shimmer"
            style={{
              textShadow: '0 4px 20px rgba(0, 0, 0, 0.5), 0 8px 40px rgba(0, 0, 0, 0.3), 0 0 60px rgba(255, 255, 255, 0.2)',
            }}
          >
            PoseFlow
          </h1>
          <p 
            className="text-2xl md:text-3xl text-white/80 font-light tracking-wide mb-12 animate-float"
            style={{
              textShadow: '0 2px 10px rgba(0, 0, 0, 0.4)',
              animationDelay: '0.3s',
            }}
          >
            Find your inner peace
          </p>
          <Button
            onClick={() => navigate("/onboarding")}
            className={`bg-white/20 hover:bg-white/30 text-white border border-white/30 text-lg px-8 py-6 transition-all duration-500 ${
              showButton 
                ? 'opacity-100 translate-y-0' 
                : 'opacity-0 translate-y-4 pointer-events-none'
            }`}
            size="lg"
            style={{
              transition: 'opacity 800ms cubic-bezier(0.16, 1, 0.3, 1), transform 800ms cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            Get Started
          </Button>
          <p className="mt-8 text-white/40 text-xs font-light max-w-xs mx-auto">
            Note: AI pose detection requires the PoseFlow backend to be running locally.
          </p>
        </div>
      </div>

      {/* Yoga Content Section - Scrollable */}
      <div 
        className="relative py-24 px-8"
        style={{
          opacity: showButton ? 1 : 0,
          transition: 'opacity 1000ms cubic-bezier(0.16, 1, 0.3, 1) 600ms',
        }}
      >
        <div className="max-w-4xl mx-auto space-y-12">
          <div className="text-center space-y-6">
            <h2 
              className="text-4xl md:text-5xl font-light text-white mb-6"
              style={{
                textShadow: '0 2px 10px rgba(0, 0, 0, 0.5)',
              }}
            >
              Yoga Unites Us All
            </h2>
            
            <p 
              className="text-xl md:text-2xl text-white/85 font-light leading-relaxed max-w-3xl mx-auto"
              style={{
                textShadow: '0 1px 5px rgba(0, 0, 0, 0.4)',
              }}
            >
              Yoga transcends boundaries, cultures, and differences. It brings together people from all walks of life, 
              creating a shared space where we connect through breath, movement, and inner peace.
            </p>
          </div>
          
          <div className="pt-12 border-t border-white/20">
            <h3 
              className="text-3xl md:text-4xl font-light text-white mb-8 text-center"
              style={{
                textShadow: '0 2px 10px rgba(0, 0, 0, 0.5)',
              }}
            >
              Why Yoga Matters
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="p-8 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10">
                <h4 className="text-xl font-normal text-white mb-3">Mind & Body Harmony</h4>
                <p className="text-base md:text-lg text-white/80 font-light leading-relaxed">
                  Yoga integrates physical movement with mindfulness, promoting overall well-being and mental clarity.
                </p>
              </div>
              
              <div className="p-8 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10">
                <h4 className="text-xl font-normal text-white mb-3">Stress Relief</h4>
                <p className="text-base md:text-lg text-white/80 font-light leading-relaxed">
                  Through breathing techniques and meditation, yoga helps reduce stress and anxiety, bringing calm to your daily life.
                </p>
              </div>
              
              <div className="p-8 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10">
                <h4 className="text-xl font-normal text-white mb-3">Physical Strength</h4>
                <p className="text-base md:text-lg text-white/80 font-light leading-relaxed">
                  Build flexibility, balance, and core strength while respecting your body's natural limits and progress.
                </p>
              </div>
              
              <div className="p-8 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10">
                <h4 className="text-xl font-normal text-white mb-3">Community Connection</h4>
                <p className="text-base md:text-lg text-white/80 font-light leading-relaxed">
                  Practice with others who share the journey, creating bonds that transcend superficial differences.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Animated Circles */}
      <div 
        className="absolute top-1/4 left-1/4 w-40 h-40 rounded-full bg-white/5 "
        style={{
          opacity: isLoaded ? 0.5 : 0,
          transform: isLoaded ? 'scale(1)' : 'scale(0.7)',
          transition: 'opacity 2500ms cubic-bezier(0.16, 1, 0.3, 1) 600ms, transform 3000ms cubic-bezier(0.34, 1.56, 0.64, 1) 600ms',
          animation: isLoaded ? 'pulse-gentle 5s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none',
          boxShadow: '0 0 60px rgba(255, 255, 255, 0.1)',
        }}
      />
      <div 
        className="absolute bottom-1/4 right-1/4 w-56 h-56 rounded-full bg-white/5 "
        style={{
          opacity: isLoaded ? 0.5 : 0,
          transform: isLoaded ? 'scale(1)' : 'scale(0.7)',
          transition: 'opacity 2500ms cubic-bezier(0.16, 1, 0.3, 1) 900ms, transform 3000ms cubic-bezier(0.34, 1.56, 0.64, 1) 900ms',
          animation: isLoaded ? 'pulse-gentle 6s cubic-bezier(0.4, 0, 0.6, 1) infinite 1.5s' : 'none',
          boxShadow: '0 0 80px rgba(255, 255, 255, 0.1)',
        }}
      />
      <div 
        className="absolute top-1/3 right-1/3 w-32 h-32 rounded-full bg-white/5 "
        style={{
          opacity: isLoaded ? 0.5 : 0,
          transform: isLoaded ? 'scale(1)' : 'scale(0.7)',
          transition: 'opacity 2500ms cubic-bezier(0.16, 1, 0.3, 1) 1200ms, transform 3000ms cubic-bezier(0.34, 1.56, 0.64, 1) 1200ms',
          animation: isLoaded ? 'pulse-gentle 7s cubic-bezier(0.4, 0, 0.6, 1) infinite 2.5s' : 'none',
          boxShadow: '0 0 50px rgba(255, 255, 255, 0.1)',
        }}
      />
      
      {/* Additional floating orbs */}
      <div 
        className="absolute top-1/2 left-1/3 w-24 h-24 rounded-full bg-white/3  animate-float"
        style={{
          opacity: isLoaded ? 0.4 : 0,
          transition: 'opacity 2000ms ease-out 1500ms',
          animationDelay: '1s',
        }}
      />
      <div 
        className="absolute bottom-1/3 left-1/5 w-20 h-20 rounded-full bg-white/3  animate-float"
        style={{
          opacity: isLoaded ? 0.4 : 0,
          transition: 'opacity 2000ms ease-out 2000ms',
          animationDelay: '2s',
        }}
      />
    </div>
  );
};

export default StartupAnimation;
