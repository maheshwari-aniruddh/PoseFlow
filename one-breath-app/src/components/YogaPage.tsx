import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import meditationBg from "@/assets/meditation-silhouette.jpg";

const YogaPage = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user has a yoga plan
    const savedPlan = localStorage.getItem("userYogaPlan");
    if (savedPlan) {
      try {
        const plan = JSON.parse(savedPlan);
        if (plan.poses && plan.poses.length > 0) {
          // Navigate to yoga session with the saved plan
          navigate("/yoga-session", { state: { plan } });
          return;
        }
      } catch (e) {
        console.error("Error parsing saved plan:", e);
      }
    }
    
    // If no plan, redirect to onboarding
    navigate("/onboarding");
  }, [navigate]);

  // Show loading while redirecting
  return (
    <div className="fixed inset-0">
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${meditationBg})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-yoga-start))]/40 to-black/50" />
      </div>
      <div className="relative z-10 h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading yoga session...</p>
        </div>
      </div>
    </div>
  );
};

export default YogaPage;
