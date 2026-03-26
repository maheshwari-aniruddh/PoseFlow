import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import StartupAnimation from "./components/StartupAnimation";
import OnboardingPage from "./components/OnboardingPage";
import YogaSessionPage from "./components/YogaSessionPage";
import PeacefulTabs from "./components/PeacefulTabs";
import PracticePage from "./components/PracticePage";
import ProgressPage from "./components/ProgressPage";
import CommunityPage from "./components/CommunityPage";

const NotFound = () => (
  <div className="fixed inset-0 flex items-center justify-center bg-gradient-to-br from-[hsl(var(--gradient-bg-start))] via-[hsl(var(--gradient-bg-mid))] to-[hsl(var(--gradient-bg-end))]">
    <div className="text-center animate-fade-in-up">
      <h1 className="mb-4 text-6xl font-light text-white">404</h1>
      <p className="mb-6 text-xl text-white/70 font-light">Oops! Page not found</p>
      <a href="/menu" className="text-white/90 underline hover:text-white font-light">
        Return to Menu
      </a>
    </div>
  </div>
);

const App = () => {
  // Error boundary wrapper
  try {
    return (
      <>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<StartupAnimation />} />
            <Route path="/onboarding" element={<OnboardingPage />} />
            <Route path="/yoga-session" element={<YogaSessionPage />} />
            <Route path="/menu" element={<PeacefulTabs />} />
            <Route path="/practice" element={<PracticePage />} />
            <Route path="/progress" element={<ProgressPage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </>
    );
  } catch (error) {
    console.error("App render error:", error);
    return (
      <div style={{ padding: '20px', fontFamily: 'sans-serif', color: 'white', background: 'black', minHeight: '100vh' }}>
        <h1>Error Loading App</h1>
        <p>{error instanceof Error ? error.message : String(error)}</p>
        <p>Check the browser console for more details.</p>
      </div>
    );
  }
};

export default App;
