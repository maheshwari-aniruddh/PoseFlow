import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Pause, Play, Square, Brain, Flower2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import meditationBg from "@/assets/meditation-silhouette.jpg";
import YogaPage from "./YogaPage";

type PracticeMode = "meditate" | "yoga" | null;
type MeditationMode = "morning" | "night" | "stress" | null;
type BreathPhase = "in" | "hold" | "out" | "pause";

interface MeditationScript {
  segments: string[];
  breathCycle: { in: number; hold: number; out: number };
}

const scripts: Record<Exclude<MeditationMode, null>, MeditationScript> = {
  morning: {
    segments: [
      "Welcome to your morning meditation. Let's begin with a deep breath in.",
      "Feel the fresh energy of a new day filling your lungs.",
      "Hold this breath, embracing the possibilities ahead.",
      "Slowly release, letting go of any tension.",
      "With each breath, feel more awake and alive.",
      "Breathe in gratitude for this new day.",
      "Hold it, feeling thankful.",
      "And breathe out, ready to embrace what comes.",
    ],
    breathCycle: { in: 4, hold: 2, out: 6 },
  },
  night: {
    segments: [
      "Welcome to your evening meditation. Take a gentle breath in.",
      "Feel your body beginning to relax.",
      "Hold this peaceful moment.",
      "Breathe out slowly, releasing the day's stress.",
      "Let each breath guide you deeper into calm.",
      "Breathe in tranquility.",
      "Hold it softly.",
      "And exhale, preparing for restful sleep.",
    ],
    breathCycle: { in: 4, hold: 2, out: 6 },
  },
  stress: {
    segments: [
      "Let's find your calm center. Breathe in deeply for four.",
      "Feel the breath filling you with peace.",
      "Hold for seven counts, staying present.",
      "Now release for eight counts, letting tension flow away.",
      "With each cycle, feel more grounded.",
      "Breathe in calm and clarity.",
      "Hold it, staying centered.",
      "And breathe out, releasing all worry.",
    ],
    breathCycle: { in: 4, hold: 7, out: 8 },
  },
};

const PracticePage = () => {
  const navigate = useNavigate();
  const [practiceMode, setPracticeMode] = useState<PracticeMode>(null);
  const [meditationMode, setMeditationMode] = useState<MeditationMode>(null);
  const [isActive, setIsActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [breathPhase, setBreathPhase] = useState<BreathPhase>("in");
  const [segmentIndex, setSegmentIndex] = useState(0);

  useEffect(() => {
    if (!isActive || isPaused || !meditationMode || practiceMode !== "meditate") return;

    let cancelled = false;
    const script = scripts[meditationMode];
    const { breathCycle } = script;
    
    const speak = (text: string) => {
      if (cancelled) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.85;
      utterance.pitch = 0.9;
      utterance.volume = 1.0;
      speechSynthesis.speak(utterance);
    };

    const runBreathCycle = async () => {
      if (cancelled) return;
      
      const currentIndex = segmentIndex;
      if (currentIndex < script.segments.length) {
        speak(script.segments[currentIndex]);
      }

      if (!cancelled) setBreathPhase("in");
      await new Promise(resolve => setTimeout(resolve, breathCycle.in * 1000));
      
      if (!cancelled) setBreathPhase("hold");
      await new Promise(resolve => setTimeout(resolve, breathCycle.hold * 1000));
      
      if (!cancelled) setBreathPhase("out");
      await new Promise(resolve => setTimeout(resolve, breathCycle.out * 1000));
      
      if (!cancelled) setBreathPhase("pause");
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      if (!cancelled) {
        setSegmentIndex(prev => (prev + 1) % script.segments.length);
      }
    };

    runBreathCycle();
    
    return () => {
      cancelled = true;
    };
  }, [isActive, isPaused, meditationMode, segmentIndex, practiceMode]);

  const startMeditation = (selectedMode: Exclude<MeditationMode, null>) => {
    // Redirect to breathbox meditation instead of using built-in meditation
    window.location.href = '/breathbox-meditation/index.html';
  };

  const stopMeditation = () => {
    setIsActive(false);
    setIsPaused(false);
    setMeditationMode(null);
    setBreathPhase("in");
    setSegmentIndex(0);
    setPracticeMode(null);
    speechSynthesis.cancel();
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
    if (!isPaused) {
      speechSynthesis.pause();
    } else {
      speechSynthesis.resume();
    }
  };

  const getBreathText = () => {
    switch (breathPhase) {
      case "in": return "Breathe In";
      case "hold": return "Hold";
      case "out": return "Breathe Out";
      case "pause": return "Rest";
    }
  };

  const getBreathScale = () => {
    if (breathPhase === "in") return "scale-[1.8]";
    if (breathPhase === "out") return "scale-100";
    return "scale-[1.8]";
  };

  if (practiceMode === "yoga") {
    return <YogaPage />;
  }

  if (!isActive && !practiceMode) {
    return (
      <div className="fixed inset-0">
        <div 
          className="absolute inset-0 bg-cover bg-center animate-fade-in"
          style={{ backgroundImage: `url(${meditationBg})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-meditation-start))]/40 to-black/50" />
        </div>

        <Button
          variant="ghost"
          onClick={() => navigate("/menu")}
          className="absolute top-6 left-6 text-white hover:bg-white/10 z-10 "
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="relative h-full flex flex-col items-center justify-center px-8">
          <h1 className="text-6xl font-light text-white mb-16 animate-fade-in-up">
            Choose Your Practice
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full mb-12">
            {/* Meditation Option */}
            <div
              onClick={() => window.location.href = '/breathbox-meditation/menu.html'}
              className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30 
 border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:from-[hsl(var(--gradient-meditation-start))]/50 hover:to-[hsl(var(--gradient-meditation-end))]/50
                animate-fade-in-up"
              style={{ animationDelay: '0.1s' }}
            >
              <Brain className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />
              <h2 className="text-3xl font-light text-white mb-4">Meditation</h2>
              <p className="text-white/70 font-light leading-relaxed">
                Guided breathing exercises and mindful meditation
              </p>
            </div>

            {/* Yoga Option */}
            <div
              onClick={() => setPracticeMode("yoga")}
              className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-yoga-start))]/30 to-[hsl(var(--gradient-yoga-end))]/30 
 border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:from-[hsl(var(--gradient-yoga-start))]/50 hover:to-[hsl(var(--gradient-yoga-end))]/50
                animate-fade-in-up"
              style={{ animationDelay: '0.2s' }}
            >
              <Flower2 className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />
              <h2 className="text-3xl font-light text-white mb-4">Yoga</h2>
              <p className="text-white/70 font-light leading-relaxed">
                Practice mindful movement and connect with your body
              </p>
            </div>
          </div>
        </div>

        <div className="absolute top-20 right-20 w-48 h-48 rounded-full bg-white/5 animate-pulse-slow" />
        <div className="absolute bottom-20 left-20 w-64 h-64 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '1.5s' }} />
      </div>
    );
  }

  if (practiceMode === "meditate" && !isActive) {
    return (
      <div className="fixed inset-0">
        <div 
          className="absolute inset-0 bg-cover bg-center animate-fade-in"
          style={{ backgroundImage: `url(${meditationBg})` }}
        >
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-meditation-start))]/40 to-black/50" />
        </div>

        <Button
          variant="ghost"
          onClick={() => setPracticeMode(null)}
          className="absolute top-6 left-6 text-white hover:bg-white/10 z-10 "
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="relative h-full flex flex-col items-center justify-center px-8">
          <h1 className="text-6xl font-light text-white mb-16 animate-fade-in-up">
            Choose Your Meditation
          </h1>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl w-full">
            <div
              onClick={() => startMeditation("morning")}
              className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30 
 border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:from-[hsl(var(--gradient-meditation-start))]/50 hover:to-[hsl(var(--gradient-meditation-end))]/50
                animate-fade-in-up"
              style={{ animationDelay: '0.1s' }}
            >
              <h2 className="text-3xl font-light text-white mb-4">Morning Meditation</h2>
              <p className="text-white/70 font-light leading-relaxed">
                Start your day with mindfulness and gratitude
              </p>
              <div className="absolute top-4 right-4 w-12 h-12 rounded-full bg-white/10 animate-pulse-slow" />
            </div>

            <div
              onClick={() => startMeditation("night")}
              className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30 
 border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:from-[hsl(var(--gradient-meditation-start))]/50 hover:to-[hsl(var(--gradient-meditation-end))]/50
                animate-fade-in-up"
              style={{ animationDelay: '0.2s' }}
            >
              <h2 className="text-3xl font-light text-white mb-4">Night Meditation</h2>
              <p className="text-white/70 font-light leading-relaxed">
                Wind down and prepare for restful sleep
              </p>
              <div className="absolute bottom-4 left-4 w-16 h-16 rounded-full bg-white/10 animate-pulse-slow" style={{ animationDelay: '1s' }} />
            </div>

            <div
              onClick={() => startMeditation("stress")}
              className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30 
 border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl hover:from-[hsl(var(--gradient-meditation-start))]/50 hover:to-[hsl(var(--gradient-meditation-end))]/50
                animate-fade-in-up"
              style={{ animationDelay: '0.3s' }}
            >
              <h2 className="text-3xl font-light text-white mb-4">Stress Relief Meditation</h2>
              <p className="text-white/70 font-light leading-relaxed">
                Find calm with focused breathing
              </p>
              <div className="absolute top-4 left-4 w-14 h-14 rounded-full bg-white/10 animate-pulse-slow" style={{ animationDelay: '2s' }} />
            </div>
          </div>
        </div>

        <div className="absolute top-20 right-20 w-48 h-48 rounded-full bg-white/5 animate-pulse-slow" />
        <div className="absolute bottom-20 left-20 w-64 h-64 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '1.5s' }} />
      </div>
    );
  }

  return (
    <div className="fixed inset-0">
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${meditationBg})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-meditation-start))]/40 to-black/50" />
      </div>

      <Button
        variant="ghost"
        onClick={stopMeditation}
        className="absolute top-6 left-6 text-white hover:bg-white/10  z-10"
      >
        <Square className="mr-2 h-4 w-4" />
        Stop
      </Button>

      <div className="relative h-full flex flex-col items-center justify-center">
        <h2 className="text-5xl font-light text-white mb-8 animate-fade-in">
          {meditationMode === "morning" ? "Morning" : meditationMode === "night" ? "Night" : "Stress Relief"} Meditation
        </h2>

        <div className="relative flex items-center justify-center mb-12">
          {/* Outer glow ring */}
          <div
            className={`absolute inset-0 w-64 h-64 rounded-full bg-white/5
              transition-all duration-[4000ms] cubic-bezier(0.4, 0, 0.2, 1)
              ${getBreathScale()}
              animate-glow-pulse`}
            style={{
              boxShadow: '0 0 60px 30px rgba(255, 255, 255, 0.1)',
            }}
          />
          
          {/* Main breathing circle */}
          <div
            className={`w-64 h-64 rounded-full bg-white/20 flex items-center justify-center
              transition-all duration-[4000ms] cubic-bezier(0.4, 0, 0.2, 1)
              ${getBreathScale()}
              backdrop-blur-sm`}
            style={{
              boxShadow: 'inset 0 0 40px rgba(255, 255, 255, 0.2), 0 0 40px rgba(255, 255, 255, 0.1)',
            }}
          >
            <div 
              className="w-48 h-48 rounded-full bg-white/30 flex items-center justify-center
                backdrop-blur-md animate-float"
              style={{
                boxShadow: 'inset 0 0 30px rgba(255, 255, 255, 0.3), 0 0 30px rgba(255, 255, 255, 0.2)',
              }}
            >
              <span className="text-2xl font-light text-white drop-shadow-lg">{getBreathText()}</span>
            </div>
          </div>
          
          {/* Inner pulse ring */}
          <div
            className={`absolute inset-0 w-64 h-64 rounded-full bg-white/5
              transition-all duration-[4000ms] cubic-bezier(0.4, 0, 0.2, 1)
              ${getBreathScale()}`}
            style={{
              boxShadow: '0 0 30px 15px rgba(255, 255, 255, 0.15)',
            }}
          />
        </div>

        <p className="text-xl text-white/80 font-light mb-12 text-center max-w-2xl px-8 animate-fade-in-up">
          {meditationMode && scripts[meditationMode].segments[segmentIndex]}
        </p>

        <Button
          onClick={togglePause}
          className="bg-white/20 hover:bg-white/30  text-white border border-white/30"
          size="lg"
        >
          {isPaused ? <Play className="mr-2 h-5 w-5" /> : <Pause className="mr-2 h-5 w-5" />}
          {isPaused ? "Resume" : "Pause"}
        </Button>
      </div>

      <div className="absolute top-1/4 left-1/4 w-32 h-32 rounded-full bg-white/5 animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-40 h-40 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '1s' }} />
      <div className="absolute top-1/3 right-1/3 w-24 h-24 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '2s' }} />
    </div>
  );
};

export default PracticePage;

