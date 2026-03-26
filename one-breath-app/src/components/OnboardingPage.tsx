import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import meditationBg from "@/assets/meditation-silhouette.jpg";

// The 24 poses from config
const AVAILABLE_POSES = [
  "Boat_Pose_or_Paripurna_Navasana_",
  "Bound_Angle_Pose_or_Baddha_Konasana_",
  "Cat_Cow_Pose_or_Marjaryasana_",
  "Chair_Pose_or_Utkatasana_",
  "Corpse_Pose_or_Savasana_",
  "Dolphin_Plank_Pose_or_Makara_Adho_Mukha_Svanasana_",
  "Extended_Puppy_Pose_or_Uttana_Shishosana_",
  "Extended_Revolved_Side_Angle_Pose_or_Utthita_Parsvakonasana_",
  "Four-Limbed_Staff_Pose_or_Chaturanga_Dandasana_",
  "Garland_Pose_or_Malasana_",
  "Gate_Pose_or_Parighasana_",
  "Happy_Baby_Pose_or_Ananda_Balasana_",
  "Locust_Pose_or_Salabhasana_",
  "Low_Lunge_pose_or_Anjaneyasana_",
  "Sitting pose 1 (normal)",
  "Staff_Pose_or_Dandasana_",
  "Plank_Pose_or_Kumbhakasana_",
  "Supta_Baddha_Konasana_",
  "Tree_Pose_or_Vrksasana_",
  "viparita_virabhadrasana_or_reverse_warrior_pose",
  "Virasana_or_Vajrasana",
  "Warrior_I_Pose_or_Virabhadrasana_I_",
  "Warrior_II_Pose_or_Virabhadrasana_II_",
  "Wind_Relieving_pose_or_Pawanmuktasana",
];

interface UserProfile {
  healthLevel: string;
  age: number;
  weight: number;
}

interface YogaPlan {
  name: string;
  poses: string[];
  hold_times: number[];
}

const OnboardingPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [healthLevel, setHealthLevel] = useState("");
  const [age, setAge] = useState("");
  const [weight, setWeight] = useState("");
  const [yogaPlan, setYogaPlan] = useState<YogaPlan | null>(null);

  const generateYogaPlan = (profile: UserProfile): YogaPlan => {
    const userAge = profile.age;
    const userWeight = profile.weight;
    const health = profile.healthLevel.toLowerCase();

    // Determine difficulty and pose selection based on inputs
    let selectedPoses: string[] = [];
    let holdTimes: number[] = [];

    // Always start with Tree Pose
    const treePose = "Tree_Pose_or_Vrksasana_";
    selectedPoses.push(treePose);
    holdTimes.push(20);

    // Easy poses for beginners/older users (from the 24 available)
    const easyPoses = [
      "Warrior_I_Pose_or_Virabhadrasana_I_",
      "Warrior_II_Pose_or_Virabhadrasana_II_",
      "Chair_Pose_or_Utkatasana_",
      "Corpse_Pose_or_Savasana_",
      "Cat_Cow_Pose_or_Marjaryasana_",
      "Happy_Baby_Pose_or_Ananda_Balasana_",
      "Wind_Relieving_pose_or_Pawanmuktasana",
    ].filter(pose => AVAILABLE_POSES.includes(pose));

    // Medium poses
    const mediumPoses = [
      "Bound_Angle_Pose_or_Baddha_Konasana_",
      "Happy_Baby_Pose_or_Ananda_Balasana_",
      "Low_Lunge_pose_or_Anjaneyasana_",
      "Gate_Pose_or_Parighasana_",
      "Virasana_or_Vajrasana",
      "Staff_Pose_or_Dandasana_",
      "Sitting pose 1 (normal)",
    ].filter(pose => AVAILABLE_POSES.includes(pose));

    // Advanced poses
    const advancedPoses = [
      "Boat_Pose_or_Paripurna_Navasana_",
      "Plank_Pose_or_Kumbhakasana_",
      "Four-Limbed_Staff_Pose_or_Chaturanga_Dandasana_",
      "Dolphin_Plank_Pose_or_Makara_Adho_Mukha_Svanasana_",
      "Extended_Revolved_Side_Angle_Pose_or_Utthita_Parsvakonasana_",
      "Locust_Pose_or_Salabhasana_",
    ].filter(pose => AVAILABLE_POSES.includes(pose));

    // Determine plan based on age, weight, and health
    let numPoses = 8; // Default
    let baseHoldTime = 20; // Default hold time in seconds

    if (userAge >= 60 || health === "poor" || userWeight > 250) {
      // Older users, poor health, or high weight - easier plan
      numPoses = 6;
      baseHoldTime = 15;
      selectedPoses.push(...easyPoses.slice(0, numPoses - 1));
      holdTimes.push(...Array(numPoses - 1).fill(baseHoldTime));
    } else if (userAge >= 40 || health === "fair" || userWeight > 200) {
      // Middle-aged or fair health - moderate plan
      numPoses = 8;
      baseHoldTime = 20;
      selectedPoses.push(...easyPoses.slice(0, 4));
      selectedPoses.push(...mediumPoses.slice(0, 3));
      holdTimes.push(...Array(4).fill(baseHoldTime));
      holdTimes.push(...Array(3).fill(baseHoldTime));
    } else if (health === "excellent" && userAge < 40 && userWeight < 200) {
      // Super healthy, young, and fit - include harder poses
      numPoses = 12;
      baseHoldTime = 30;
      selectedPoses.push(...easyPoses.slice(0, 2));
      selectedPoses.push(...mediumPoses.slice(0, 4));
      selectedPoses.push(...advancedPoses.slice(0, 5)); // More advanced poses
      holdTimes.push(...Array(2).fill(baseHoldTime));
      holdTimes.push(...Array(4).fill(baseHoldTime));
      holdTimes.push(...Array(5).fill(baseHoldTime));
    } else {
      // Younger, good health - moderate challenging plan
      numPoses = 10;
      baseHoldTime = 25;
      selectedPoses.push(...easyPoses.slice(0, 3));
      selectedPoses.push(...mediumPoses.slice(0, 4));
      selectedPoses.push(...advancedPoses.slice(0, 2));
      holdTimes.push(...Array(3).fill(baseHoldTime));
      holdTimes.push(...Array(4).fill(baseHoldTime));
      holdTimes.push(...Array(2).fill(baseHoldTime));
    }

    // Ensure we only use available poses and don't exceed 24
    selectedPoses = selectedPoses.filter(pose => AVAILABLE_POSES.includes(pose));
    selectedPoses = selectedPoses.slice(0, Math.min(selectedPoses.length, 24));

    // Adjust hold times to match
    holdTimes = holdTimes.slice(0, selectedPoses.length);

    return {
      name: "Personalized Yoga Plan",
      poses: selectedPoses,
      hold_times: holdTimes,
    };
  };

  const handleSubmit = () => {
    if (!healthLevel || !age || !weight) {
      alert("Please fill in all fields");
      return;
    }

    const profile: UserProfile = {
      healthLevel,
      age: parseInt(age),
      weight: parseFloat(weight),
    };

    const plan = generateYogaPlan(profile);
    setYogaPlan(plan);

    // Store in localStorage
    localStorage.setItem("userProfile", JSON.stringify(profile));
    localStorage.setItem("yogaPlan", JSON.stringify(plan));

    setStep(3);
  };

  if (step === 3 && yogaPlan) {
    return (
      <div 
        className="min-h-screen relative flex items-center justify-center px-8"
        style={{
          backgroundImage: `url(${meditationBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-black/60" />
        <div className="relative z-10 max-w-2xl w-full bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
          <h2 className="text-4xl font-light text-white mb-6 text-center">
            Your Personalized Yoga Plan
          </h2>
          <div className="space-y-4 mb-8">
            <div className="bg-white/10 rounded-lg p-4">
              <p className="text-white/90 text-lg mb-2">
                <strong>Health Level:</strong> {healthLevel}
              </p>
              <p className="text-white/90 text-lg mb-2">
                <strong>Age:</strong> {age} years
              </p>
              <p className="text-white/90 text-lg">
                <strong>Weight:</strong> {weight} lbs
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <p className="text-white/90 text-lg mb-4">
                <strong>Plan:</strong> {yogaPlan.poses.length} poses
              </p>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {yogaPlan.poses.map((pose, idx) => (
                  <div key={idx} className="text-white/80 text-sm">
                    {idx + 1}. {pose.replace(/_/g, " ").replace(/or/g, "|")} ({yogaPlan.hold_times[idx]}s)
                  </div>
                ))}
              </div>
            </div>
          </div>
          <Button
            onClick={() => {
              // Save plan to localStorage and navigate to menu
              try {
                localStorage.setItem("userYogaPlan", JSON.stringify(yogaPlan));
                console.log("Navigating to /menu...");
                navigate("/menu", { replace: true });
              } catch (error) {
                console.error("Navigation error:", error);
                // Fallback: try direct navigation
                window.location.href = "/menu";
              }
            }}
            className="w-full bg-white/20 hover:bg-white/30 text-white border border-white/30 text-lg py-6"
            size="lg"
          >
            Continue to Menu
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen relative flex items-center justify-center px-8"
      style={{
        backgroundImage: `url(${meditationBg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      <div className="absolute inset-0 bg-black/60" />
      <div className="relative z-10 max-w-2xl w-full bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
        <h2 className="text-4xl font-light text-white mb-8 text-center">
          {step === 1 ? "Welcome to PoseFlow" : "Tell Us About Yourself"}
        </h2>

        {step === 1 ? (
          <div className="space-y-6">
            <p className="text-white/90 text-lg text-center">
              Let's create a personalized yoga plan just for you
            </p>
            <Button
              onClick={() => setStep(2)}
              className="w-full bg-white/20 hover:bg-white/30 text-white border border-white/30 text-lg py-6"
              size="lg"
            >
              Get Started
            </Button>
            <Button
              onClick={() => navigate("/practice")}
              className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/20 text-sm py-3"
              variant="outline"
            >
              Skip to Practice
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <label className="block text-white/90 text-lg mb-2">
                Health Level
              </label>
              <select
                value={healthLevel}
                onChange={(e) => setHealthLevel(e.target.value)}
                className="w-full bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-white/50"
              >
                <option value="">Select health level</option>
                <option value="excellent">Excellent</option>
                <option value="good">Good</option>
                <option value="fair">Fair</option>
                <option value="poor">Poor</option>
              </select>
            </div>

            <div>
              <label className="block text-white/90 text-lg mb-2">
                Age
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="Enter your age"
                className="w-full bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>

            <div>
              <label className="block text-white/90 text-lg mb-2">
                Weight (lbs)
              </label>
              <input
                type="number"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                placeholder="Enter your weight in pounds"
                className="w-full bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
            </div>

            <div className="flex gap-4">
              <Button
                onClick={() => setStep(1)}
                className="flex-1 bg-white/10 hover:bg-white/20 text-white border border-white/30"
              >
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                className="flex-1 bg-white/20 hover:bg-white/30 text-white border border-white/30"
                disabled={!healthLevel || !age || !weight}
              >
                Create Plan
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingPage;

