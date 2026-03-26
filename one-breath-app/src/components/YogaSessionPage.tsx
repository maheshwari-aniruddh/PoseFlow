import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Pause, Play, Square } from "lucide-react";
import { io, Socket } from "socket.io-client";
import HUDOverlay from "./HUDOverlay";
import QuoteOfTheDay from "./QuoteOfTheDay";
import meditationBg from "@/assets/meditation-silhouette.jpg";

/** Play a gentle chime when a session segment ends (pure Web Audio, no API) */
const playSegmentEndSound = () => {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 523.25;
    osc.type = "sine";
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.4);
  } catch {
    /* ignore */
  }
};

/** Play a two-tone completion chime when the full session ends */
const playSessionCompleteSound = () => {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const playTone = (freq: number, start: number, dur: number) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = freq;
      osc.type = "sine";
      gain.gain.setValueAtTime(0.2, start);
      gain.gain.exponentialRampToValueAtTime(0.01, start + dur);
      osc.start(start);
      osc.stop(start + dur);
    };
    playTone(523.25, ctx.currentTime, 0.3);
    playTone(659.25, ctx.currentTime + 0.2, 0.5);
  } catch {
    /* ignore */
  }
};


interface YogaPlan {
  name: string;
  poses: string[];
  hold_times: number[];
}

interface SessionStatistics {
  accuracyScore: number;
  progressScore: number;
  repCount: number;
  avgHoldDuration: number;
  maxHoldDuration: number;
  avgHoldRatio: number;
  avgFormScore: number;
  correctionsCount: number;
  dangerousCorrections: number;
  improvableCorrections: number;
  consistencyScore: number;
  sessionDuration: number;
  poseEntries: number;
}

interface DebugInfo {
  detected_pose?: string;
  target_pose?: string;
  pose_confidence?: number;
  angle_similarity?: number;
  combined_score?: number;
  has_template?: boolean;
  exact_match?: boolean;
  body_fully_visible?: boolean;
  stability_frames?: number;
  stability_required?: number;
  smoothed_score?: number;
  can_start_timer?: boolean;
  is_matching_pose?: boolean;
}

interface SessionState {
  currentPoseIndex: number;
  currentPose: string;
  holdTime: number;
  elapsedTime: number;
  isInPose: boolean;
  poseStatus: "correct" | "improvable" | "wrong" | "unknown";
  feedback: string;
  sessionActive: boolean;
  statistics: SessionStatistics | null;
  poseImage: string | null;  // Base64 encoded pose image
  debugInfo: DebugInfo | null;  // Debug information
  videoFrame?: string | null; // Video frame data
}

const YogaSessionPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Get plan from location state or localStorage
  const planFromState = location.state?.plan;
  const planFromStorage = localStorage.getItem("userYogaPlan");

  let plan: YogaPlan;
  if (planFromState) {
    plan = planFromState;
  } else if (planFromStorage) {
    try {
      plan = JSON.parse(planFromStorage);
    } catch {
      plan = { name: "Default", poses: [], hold_times: [] };
    }
  } else {
    plan = { name: "Default", poses: [], hold_times: [] };
  }

  const [sessionState, setSessionState] = useState<SessionState>({
    currentPoseIndex: 0,
    currentPose: plan.poses?.[0] || "",
    holdTime: plan.hold_times?.[0] || 20,
    elapsedTime: 0,
    isInPose: false,
    poseStatus: "unknown",
    feedback: "",
    sessionActive: false,
    statistics: null,
    poseImage: null,  // Pose reference image
    debugInfo: null,  // Debug information
  });

  const [isPaused, setIsPaused] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [videoFrame, setVideoFrame] = useState<string | null>(null);
  const [availableCameras, setAvailableCameras] = useState<Array<{ id: number, name: string, width: number, height: number }>>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<number>(0);
  const [loadingCameras, setLoadingCameras] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const loadingRef = useRef(false);
  const cameraActiveRef = useRef(false);
  const videoRef = useRef<HTMLImageElement | null>(null);
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);

  // Redirect to onboarding if no plan
  useEffect(() => {
    if (!plan?.poses || plan.poses.length === 0) {
      navigate("/onboarding");
    }
  }, [plan, navigate]);

  // Fetch available cameras
  const fetchCameras = async () => {
    setLoadingCameras(true);
    try {
      const response = await fetch("http://localhost:5002/list-cameras");
      if (response.ok) {
        const data = await response.json();
        if (data.cameras && data.cameras.length > 0) {
          setAvailableCameras(data.cameras);
          setSelectedCameraId(data.cameras[0].id);
        }
      }
    } catch (error) {
      console.error("Error fetching cameras:", error);
    } finally {
      setLoadingCameras(false);
    }
  };

  // Fetch cameras on mount
  useEffect(() => {
    fetchCameras();
  }, []);

  // Format pose name for display
  const formatPoseName = (pose: string) => {
    return pose
      .replace(/_/g, " ")
      .replace(/or/g, "|")
      .replace(/\s+/g, " ")
      .trim();
  };

  // Start yoga session
  const startSession = async () => {
    setLoading(true);
    loadingRef.current = true;
    setSessionState(prev => ({ ...prev, sessionActive: true }));

    try {
      // Request camera access from browser first (this will show in macOS menu bar)
      console.log("📷 Requesting camera access...");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1920 },
            height: { ideal: 1080 },
            facingMode: 'user'
          },
          audio: false
        });
        localStreamRef.current = stream;

        // Attach to video element (even if hidden) to keep stream active
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = stream;
          localVideoRef.current.play().catch(e => console.log("Video play error:", e));
        }

        console.log("✅ Camera access granted");
        setCameraActive(true);
        cameraActiveRef.current = true;
      } catch (cameraError: any) {
        console.error("❌ Camera access denied:", cameraError);
        // Continue anyway - backend will use its own camera
        // But show warning to user
        if (cameraError.name === 'NotAllowedError' || cameraError.name === 'PermissionDeniedError') {
          alert("Camera permission denied. The app will use the backend camera, but you may need to grant camera permission in System Settings.");
        }
      }

      // Check if backend is available first
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const healthCheck = await fetch("http://localhost:5002/health", {
        method: "GET",
        signal: controller.signal,
      }).catch(() => {
        clearTimeout(timeoutId);
        return null;
      });
      clearTimeout(timeoutId);

      if (!healthCheck || !healthCheck.ok) {
        throw new Error("Yoga backend server is not running. Please start it with: ./start_yoga_web.sh");
      }

      // Start backend yoga session
      const sessionController = new AbortController();
      const sessionTimeoutId = setTimeout(() => sessionController.abort(), 20000); // Increased to 20 seconds for camera initialization

      const response = await fetch("http://localhost:5002/start-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, camera_id: selectedCameraId }),
        signal: sessionController.signal,
      }).catch((error) => {
        clearTimeout(sessionTimeoutId);
        if (error.name === 'AbortError') {
          throw new Error("Request timeout. Camera initialization may be slow. Please try again.");
        }
        throw new Error(`Failed to connect: ${error.message}`);
      });
      clearTimeout(sessionTimeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || errorData.error || `Failed to start session (${response.status})`;
        console.error("Start session error:", errorData);
        throw new Error(errorMessage);
      }

      // Connect Socket.IO for real-time updates
      const socket = io("http://localhost:5002", {
        timeout: 5000,
        transports: ['websocket', 'polling'],
      });
      socketRef.current = socket;

      // Store timeout reference for cleanup
      let connectionTimeoutRef: NodeJS.Timeout | null = null;

      // Set up timeout BEFORE connect handler
      connectionTimeoutRef = setTimeout(() => {
        if (loadingRef.current && !cameraActiveRef.current) {
          setLoading(false);
          loadingRef.current = false;
          setSessionState(prev => ({ ...prev, sessionActive: false }));
          if (socketRef.current) {
            socketRef.current.disconnect();
          }
          alert("Connection timeout. Please check if the backend is running.");
        }
      }, 10000);

      socket.on("connect", () => {
        console.log("✅ Socket.IO connected - ready to receive video frames");
        if (connectionTimeoutRef) {
          clearTimeout(connectionTimeoutRef);
          connectionTimeoutRef = null;
        }
        setLoading(false);
        loadingRef.current = false;
        setCameraActive(true);
        cameraActiveRef.current = true;
      });

      socket.on("connected", (data: any) => {
        console.log("✅ Server confirmed connection:", data);
      });

      socket.on("session_update", (data: any) => {
        try {
          // Log video frame in session_update
          if (data?.videoFrame || data?.video_frame) {
            const frame = data.videoFrame || data.video_frame;
            console.log(`📹 Video frame in session_update: ${frame?.length || 0} chars`);
          }

          // Safely extract all values with fallbacks
          const holdTime = data.holdTime ?? data.hold_time ?? data.target_hold ?? 20;
          const elapsedTime = data.elapsedTime ?? data.elapsed_time ?? 0;

          // Extract statistics if provided - ensure all values are numbers
          const statistics = data.statistics ? {
            accuracyScore: typeof data.statistics.accuracyScore === 'number' ? data.statistics.accuracyScore : 0,
            progressScore: typeof data.statistics.progressScore === 'number' ? data.statistics.progressScore : 0,
            repCount: typeof data.statistics.repCount === 'number' ? data.statistics.repCount : 0,
            avgHoldDuration: typeof data.statistics.avgHoldDuration === 'number' ? data.statistics.avgHoldDuration : 0,
            maxHoldDuration: typeof data.statistics.maxHoldDuration === 'number' ? data.statistics.maxHoldDuration : 0,
            avgHoldRatio: typeof data.statistics.avgHoldRatio === 'number' ? data.statistics.avgHoldRatio : 0,
            avgFormScore: typeof data.statistics.avgFormScore === 'number' ? data.statistics.avgFormScore : 0,
            correctionsCount: typeof data.statistics.correctionsCount === 'number' ? data.statistics.correctionsCount : 0,
            dangerousCorrections: typeof data.statistics.dangerousCorrections === 'number' ? data.statistics.dangerousCorrections : 0,
            improvableCorrections: typeof data.statistics.improvableCorrections === 'number' ? data.statistics.improvableCorrections : 0,
            consistencyScore: typeof data.statistics.consistencyScore === 'number' ? data.statistics.consistencyScore : 0,
            sessionDuration: typeof data.statistics.sessionDuration === 'number' ? data.statistics.sessionDuration : 0,
            poseEntries: typeof data.statistics.poseEntries === 'number' ? data.statistics.poseEntries : 0,
          } : null;

          setSessionState((prev) => {
            // Use backend elapsedTime directly - backend calculates it consistently every frame
            const newElapsedTime = data.elapsedTime ?? data.elapsed_time ?? 0;

            return {
              ...prev,
              currentPoseIndex: data.currentPoseIndex ?? prev.currentPoseIndex,
              currentPose: data.currentPose ?? prev.currentPose,
              holdTime: holdTime,
              isInPose: data.isInPose ?? prev.isInPose,
              poseStatus: data.poseStatus ?? prev.poseStatus,
              feedback: data.feedback ?? prev.feedback,
              elapsedTime: newElapsedTime,  // Use backend value directly - no stabilization needed
              statistics: statistics ?? prev.statistics, // Keep previous stats if not provided
              poseImage: data.poseImage ?? data.pose_image ?? prev.poseImage,  // Add pose image
              debugInfo: data.debugInfo ?? data.debug_info ?? prev.debugInfo,  // Add debug info
            };
          });

          // Update video frame if provided
          if (data?.videoFrame || data?.video_frame) {
            try {
              const frame = data.videoFrame || data.video_frame;
              if (frame && typeof frame === 'string' && frame.length > 0) {
                const dataUrl = frame.startsWith('data:') ? frame : `data:image/jpeg;base64,${frame}`;
                setVideoFrame(dataUrl);
                console.log(`✅ Video frame received in session_update: ${frame.length} chars`);
              } else {
                console.warn("⚠️ Empty or invalid video frame in session_update", { frame, type: typeof frame });
              }
            } catch (e) {
              console.error("Error setting video frame:", e);
            }
          } else {
            // Only warn occasionally to avoid spam
            if (!sessionState.videoFrame) {
              console.warn("⚠️ No videoFrame in session_update", Object.keys(data));
            }
          }
        } catch (error) {
          console.error("Error processing session_update:", error);
          // Don't crash the session, just log the error
        }
      });

      socket.on("video_frame", (data: any) => {
        // Update video frame even if no pose info
        console.log("📹 video_frame event received", {
          hasData: !!data,
          hasFrame: !!data?.frame,
          frameType: typeof data?.frame,
          frameLength: data?.frame?.length
        });

        if (data?.frame && typeof data.frame === 'string' && data.frame.length > 0) {
          const dataUrl = data.frame.startsWith('data:') ? data.frame : `data:image/jpeg;base64,${data.frame}`;
          console.log(`✅ Setting video frame: ${data.frame.length} chars, dataUrl length: ${dataUrl.length}`);
          setVideoFrame(dataUrl);
        } else {
          console.warn("⚠️ Empty or invalid video_frame event", {
            hasData: !!data,
            hasFrame: !!data?.frame,
            frameType: typeof data?.frame,
            frameLength: data?.frame?.length
          });
        }
      });

      socket.on("debug_update", (data: any) => {
        // Update debug info separately for faster updates
        try {
          if (data && data.debugInfo) {
            setSessionState((prev) => ({
              ...prev,
              debugInfo: data.debugInfo,
            }));
          }
        } catch (error) {
          console.error("Error updating debug info:", error);
        }
      });

      // Handle pose change event from backend
      socket.on("pose_changed", (data: any) => {
        playSegmentEndSound();
        console.log("🔄 Pose changed:", data);
        setSessionState((prev) => ({
          ...prev,
          currentPoseIndex: data.currentPoseIndex ?? prev.currentPoseIndex,
          currentPose: data.currentPose ?? prev.currentPose,
          holdTime: data.holdTime ?? prev.holdTime,
          elapsedTime: 0,  // Reset timer for new pose
          isInPose: false,  // Reset pose status
          poseStatus: "unknown",
          feedback: "",
        }));
      });

      // Handle session complete
      socket.on("session_complete", (data: any) => {
        playSessionCompleteSound();
        alert("🎉 All poses completed! Great job!");
        endSession();
      });

      socket.on("error", (data: any) => {
        console.error("❌ Backend error received:", data);
        const errorMessage = data?.message || "Unknown error from backend";
        console.error("Error details:", errorMessage);
        setLoading(false);
        loadingRef.current = false;
        setSessionState(prev => ({ ...prev, sessionActive: false }));
        alert(`Backend Error: ${errorMessage}\n\nCheck the backend terminal for detailed error messages.`);
      });

      socket.on("connect_error", (error: any) => {
        console.error("Socket connection error:", error);
        setLoading(false);
        loadingRef.current = false;
        setSessionState(prev => ({ ...prev, sessionActive: false }));
        alert("Failed to connect to yoga backend. Please make sure ./start_yoga_web.sh is running.");
      });

      socket.on("disconnect", () => {
        console.log("Socket.IO disconnected");
        setCameraActive(false);
        cameraActiveRef.current = false;
      });

    } catch (error: any) {
      console.error("Failed to start session:", error);
      setLoading(false);
      loadingRef.current = false;
      setSessionState(prev => ({ ...prev, sessionActive: false }));
      alert(error.message || "Failed to start yoga session. Make sure the backend is running with: ./start_yoga_web.sh");
    }
  };

  // Timer effect - REMOVED: Use backend elapsedTime only, don't increment locally
  // The backend sends elapsedTime updates every frame, so we don't need local incrementing
  // This prevents conflicts and ensures consistency
  useEffect(() => {
    // Clear any existing interval - we rely on backend updates only
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Keyboard controls: N=next, Q=quit, R=repeat, Space=pause
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ignore if typing in input fields
      if ((e.target as HTMLElement)?.tagName === 'INPUT' || (e.target as HTMLElement)?.tagName === 'TEXTAREA') {
        return;
      }

      if (e.key.toLowerCase() === 'n' && sessionState.sessionActive) {
        nextPose();
      } else if (e.key.toLowerCase() === 'q' && sessionState.sessionActive) {
        endSession();
      } else if (e.key.toLowerCase() === 'r' && sessionState.sessionActive) {
        repeatInstruction();
      } else if (e.key === ' ' && sessionState.sessionActive) {
        e.preventDefault();
        togglePause();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [sessionState.sessionActive]);

  // Repeat instruction
  const repeatInstruction = () => {
    if (socketRef.current && sessionState.sessionActive) {
      socketRef.current.emit('repeat_instruction');
    }
  };

  // Toggle pause
  const togglePause = () => {
    const newPausedState = !isPaused;
    setIsPaused(newPausedState);

    if (socketRef.current) {
      if (newPausedState) {
        socketRef.current.emit('pause_session');
      } else {
        socketRef.current.emit('resume_session');
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Next pose - SKIP TO NEXT POSE
  const nextPose = () => {
    // Always send next_pose command to backend
    // Backend will handle the pose change and emit pose_changed event
    if (socketRef.current && sessionState.sessionActive) {
      socketRef.current.emit("next_pose");
      console.log("➡️  Skipping to next pose...");
    }
  };

  // End session
  const endSession = async () => {
    // Stop local camera stream
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }

    if (socketRef.current) {
      socketRef.current.emit("end_session");
    }

    // Stop backend session and get final statistics
    try {
      const response = await fetch("http://localhost:5002/stop-session", { method: "POST" });
      const data = await response.json();

      // Save final statistics to localStorage for progress page
      if (data.finalStatistics) {
        const savedStats = JSON.parse(localStorage.getItem("yogaSessionStats") || "[]");
        savedStats.push({
          ...data.finalStatistics,
          timestamp: new Date().toISOString(),
          planName: plan.name,
        });
        localStorage.setItem("yogaSessionStats", JSON.stringify(savedStats));
      }
    } catch (error) {
      console.error("Error stopping session:", error);
    }

    if (socketRef.current) {
      socketRef.current.disconnect();
    }

    navigate("/menu");
  };

  const progress = sessionState.holdTime > 0 ? (sessionState.elapsedTime / sessionState.holdTime) * 100 : 0;
  const remainingTime = Math.max(0, (sessionState.holdTime || 0) - (sessionState.elapsedTime || 0));

  // Get status color
  const getStatusColor = () => {
    switch (sessionState.poseStatus) {
      case "correct":
        return "bg-green-500";
      case "improvable":
        return "bg-yellow-500";
      case "wrong":
        return "bg-red-500";
      default:
        return "bg-gray-400";
    }
  };

  // Get status text
  const getStatusText = () => {
    switch (sessionState.poseStatus) {
      case "correct":
        return "Perfect Form!";
      case "improvable":
        return "Good, but can improve";
      case "wrong":
        return "Adjust your pose";
      default:
        return "Getting ready...";
    }
  };

  if (!plan?.poses || plan.poses.length === 0) {
    return null; // Will redirect via useEffect
  }

  if (!sessionState.sessionActive) {
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
        <div className="relative z-10 max-w-2xl w-full text-center">
          <h2 className="text-4xl font-light text-white mb-6">
            Ready to Begin?
          </h2>
          <p className="text-white/80 text-lg mb-8">
            {plan.poses?.length || 0} poses • {plan.hold_times && plan.hold_times.length > 0 ? Math.round(plan.hold_times.reduce((a, b) => (a || 0) + (b || 0), 0) / 60) : 0} minutes
          </p>

          {/* Camera Selection */}
          {availableCameras.length > 0 && (
            <div className="mb-6 bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
              <label className="block text-white/90 text-sm mb-2 text-left">
                Select Camera:
              </label>
              <select
                value={selectedCameraId}
                onChange={(e) => setSelectedCameraId(Number(e.target.value))}
                className="w-full bg-white/20 text-white border border-white/30 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-white/50"
              >
                {availableCameras.map((cam) => (
                  <option key={cam.id} value={cam.id} className="bg-gray-800">
                    {cam.name} ({cam.width}x{cam.height})
                  </option>
                ))}
              </select>
            </div>
          )}

          {loadingCameras && (
            <div className="mb-6 text-white/60 text-sm">
              Loading cameras...
            </div>
          )}

          <div className="mb-8 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-left">
            <p className="text-yellow-200/90 text-sm font-light leading-relaxed">
              <strong>⚠️ Local Backend Required:</strong> Real-time pose detection and AI feedback will only work if the 
              PoseFlow backend server is running on your computer. If you are viewing this on GitHub Pages, 
              please ensure you have started the local server using <code>./start_yoga_web.sh</code>.
            </p>
          </div>

          <div className="flex gap-4 justify-center">
            <Button
              onClick={() => navigate("/menu")}
              className="bg-white/10 hover:bg-white/20 text-white border border-white/30"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            <Button
              onClick={startSession}
              className="bg-white/20 hover:bg-white/30 text-white border border-white/30 text-lg px-8 py-6"
              size="lg"
            >
              Start Session
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div
        className="min-h-screen relative flex items-center justify-center"
        style={{
          backgroundImage: `url(${meditationBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="absolute inset-0 bg-black/60" />
        <div className="relative z-10 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading yoga session...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Hidden video element to keep camera stream active (shows in macOS menu bar) */}
      <video
        ref={localVideoRef}
        autoPlay
        playsInline
        muted
        style={{ position: 'absolute', width: '1px', height: '1px', opacity: 0, pointerEvents: 'none', zIndex: -1 }}
        className="hidden"
      />
      <div className="min-h-screen relative overflow-hidden bg-black">
        {/* Dynamic Background */}
        <div
          className={`absolute inset-0 transition-opacity duration-1000 ${sessionState.isInPose ? 'opacity-0' : 'opacity-40'
            }`}
          style={{
            backgroundImage: `url(${meditationBg})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />

        {/* Animated Gradients */}
        <div className={`absolute inset-0 opacity-30 transition-all duration-1000 ${sessionState.isInPose
          ? 'bg-gradient-to-br from-green-900 via-emerald-900 to-cyan-900 animate-pulse-slow'
          : 'bg-gradient-to-br from-purple-900 via-blue-900 to-black animate-gradient-shift'
          }`} />

        {/* Grid Overlay for Tech Feel */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:50px_50px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_100%)] pointer-events-none" />
        <div className="absolute inset-0 bg-black/60" />

        {/* Header */}
        <div className="relative z-10 p-6 flex justify-between items-center">
          <Button
            onClick={endSession}
            className="bg-white/10 hover:bg-white/20 text-white border border-white/30"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            End Session
          </Button>

          <div className="text-white/80 text-sm">
            Pose {sessionState.currentPoseIndex + 1} of {plan?.poses?.length || 0}
          </div>
        </div>

        {/* Main Content */}
        <div className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-120px)] px-8 py-8">
          {/* Current Pose Name and Reference Image */}
          <div className="text-center mb-6 relative w-full max-w-6xl animate-fade-in-up">
            <h2 className="text-4xl md:text-5xl font-light text-white mb-2 drop-shadow-2xl animate-shimmer">
              {formatPoseName(sessionState.currentPose)}
            </h2>
            <p className="text-white/70 text-lg animate-float" style={{ animationDelay: '0.2s' }}>
              Hold for {sessionState.holdTime} seconds
            </p>
          </div>

          {/* Video Feed + Dataset Reference Side by Side */}
          {videoFrame ? (
            <div className="mb-8 w-full max-w-6xl flex flex-col md:flex-row gap-4 md:gap-6 items-stretch justify-center animate-scale-in-bounce">
              {/* Live Video Feed - Left */}
              <div className="flex-1 min-w-0 relative bg-black/80 rounded-lg overflow-hidden shadow-2xl border-2 border-white/30 animate-glow-pulse" style={{ aspectRatio: '16/9' }}>
                <img
                  ref={videoRef}
                  src={videoFrame}
                  alt="Yoga pose detection"
                  className="w-full h-full object-contain"
                  style={{ display: 'block' }}
                  onError={(e) => {
                    console.error("❌ Image load error:", e);
                    console.error("Frame data length:", videoFrame?.length);
                  }}
                  onLoad={() => {
                    console.log("✅ Video frame image loaded successfully");
                  }}
                />
                <div className="absolute inset-0 rounded-lg pointer-events-none"
                  style={{
                    boxShadow: 'inset 0 0 40px rgba(255, 255, 255, 0.1), 0 0 60px rgba(255, 255, 255, 0.15)',
                    animation: 'glow-pulse 3s ease-in-out infinite'
                  }}
                />
                <HUDOverlay
                  isVisible={true}
                  debugInfo={sessionState.debugInfo}
                  statistics={sessionState.statistics}
                />
              </div>

              {/* Dataset Reference - Right Side Panel */}
              <div className="md:w-72 flex-shrink-0 flex flex-col">
                <div className="bg-white/95 backdrop-blur-md rounded-xl p-3 border-2 border-white shadow-xl h-full flex flex-col">
                  <p className="text-gray-700 text-xs uppercase tracking-widest font-semibold mb-2 text-center">
                    Target Pose (Dataset)
                  </p>
                  {sessionState.poseImage ? (
                    <div className="flex-1 min-h-[200px] rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={`data:image/jpeg;base64,${sessionState.poseImage}`}
                        alt={`Reference: ${formatPoseName(sessionState.currentPose)}`}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="flex-1 min-h-[200px] rounded-lg bg-gray-100 flex items-center justify-center">
                      <p className="text-gray-500 text-sm text-center px-2">
                        No reference image for this pose
                      </p>
                    </div>
                  )}
                  <p className="text-gray-600 text-xs mt-2 text-center font-medium truncate" title={sessionState.currentPose}>
                    {formatPoseName(sessionState.currentPose)}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="mb-8 w-full max-w-4xl flex justify-center animate-fade-in">
              <div className="relative bg-black/80 rounded-lg overflow-hidden shadow-2xl border-2 border-white/30 flex items-center justify-center animate-glow-pulse" style={{ aspectRatio: '16/9', minHeight: '400px' }}>
                <div className="text-center">
                  <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-white mx-auto mb-4 animate-glow-pulse"></div>
                  <div className="animate-pulse text-white/60 text-lg animate-shimmer">Waiting for camera feed...</div>
                </div>
              </div>
            </div>
          )}

          {/* Quote of the Day - compact */}
          <div className="mb-4 w-full max-w-md">
            <QuoteOfTheDay compact />
          </div>

          {/* Status and Controls Row - visible countdown timer */}
          <div className="flex flex-col md:flex-row items-center justify-center gap-8 w-full max-w-6xl">
            {/* Status Circle */}
            <div className="relative w-48 h-48">
              {/* Outer ring - progress */}
              <svg className="w-48 h-48 transform -rotate-90">
                <circle
                  cx="96"
                  cy="96"
                  r="90"
                  stroke="rgba(255,255,255,0.3)"
                  strokeWidth="6"
                  fill="none"
                />
                <circle
                  cx="96"
                  cy="96"
                  r="90"
                  stroke="white"
                  strokeWidth="6"
                  fill="none"
                  strokeDasharray={`${2 * Math.PI * 90}`}
                  strokeDashoffset={`${2 * Math.PI * 90 * (1 - progress / 100)}`}
                  className="transition-all duration-300"
                />
              </svg>

              {/* Status circle */}
              <div
                className={`absolute inset-0 rounded-full ${getStatusColor()} transition-all duration-500 flex items-center justify-center shadow-2xl animate-glow-pulse`}
                style={{
                  width: "150px",
                  height: "150px",
                  left: "50%",
                  top: "50%",
                  transform: "translate(-50%, -50%)",
                  opacity: sessionState.isInPose ? 1 : 0.4,
                  boxShadow: '0 0 40px rgba(255, 255, 255, 0.2), inset 0 0 30px rgba(255, 255, 255, 0.1)',
                }}
              >
                <div className="text-center">
                  <div className="text-white text-3xl font-light mb-1">
                    {remainingTime}s
                  </div>
                  <div className="text-white/90 text-xs">
                    {getStatusText()}
                  </div>
                </div>
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-col gap-3">
              <Button
                onClick={togglePause}
                className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
              >
                {isPaused ? (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Resume (Space)
                  </>
                ) : (
                  <>
                    <Pause className="mr-2 h-4 w-4" />
                    Pause (Space)
                  </>
                )}
              </Button>

              {sessionState.currentPoseIndex < (plan?.poses?.length || 0) - 1 && (
                <Button
                  onClick={nextPose}
                  className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
                >
                  Skip to Next (N)
                </Button>
              )}

              <Button
                onClick={repeatInstruction}
                className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
              >
                Repeat Instruction (R)
              </Button>

              <Button
                onClick={endSession}
                className="bg-red-500/20 hover:bg-red-500/30 text-white border border-red-500/30"
              >
                Quit Session (Q)
              </Button>

              {/* Camera Status */}
              <div className="flex items-center gap-2 bg-white/10 px-3 py-2 rounded-full justify-center">
                <div className={`w-2 h-2 rounded-full ${cameraActive ? "bg-green-500" : "bg-red-500"}`}></div>
                <span className="text-white/80 text-xs">
                  {cameraActive ? "Camera Active" : "Camera Inactive"}
                </span>
              </div>
            </div>
          </div>

          {/* Feedback */}
          {sessionState.feedback && (
            <div className="mt-8 max-w-2xl w-full">
              <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
                <p className="text-white text-center text-lg">{sessionState.feedback}</p>
              </div>
            </div>
          )}

        </div>
      </div>
    </>
  );
};

export default YogaSessionPage;

