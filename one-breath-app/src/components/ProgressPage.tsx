import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Calendar, BookOpen, BarChart3, Activity, Menu, X, Heart, Smile, Meh } from "lucide-react"; import { Button } from "@/components/ui/button"; import meditationBg from "@/assets/meditation-silhouette.jpg"; type ProgressView = "calendar" | "journal" | "stats" | "body" | null; type Sentiment = "happy" | "grateful" | "peaceful" | "neutral" | "reflective"; interface JournalEntry {   id: string;   date: string;   entry: string;
  sentiment: Sentiment;
} interface SessionStats {
  accuracyScore: number;   progressScore: number;
  repCount: number;
  avgHoldDuration: number;   maxHoldDuration: number;
  avgHoldRatio: number;   avgFormScore: number;   correctionsCount: number;   dangerousCorrections: number;   improvableCorrections: number;   consistencyScore: number;   sessionDuration: number;   poseEntries: number;   timestamp: string;   planName?: string; } const ProgressPage = () => {
  const navigate = useNavigate();   const [view, setView] = useState<ProgressView>(null);   const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([     { id: "1", date: "Today", entry: "I'm grateful for the peaceful morning and the opportunity to practice mindfulness.", sentiment: "grateful" },
    { id: "2", date: "Yesterday", entry: "Grateful for the support of my community and the progress I'm making on my journey.", sentiment: "grateful" },
    { id: "3", date: "2 days ago", entry: "Thankful for my body's strength and the ability to practice yoga today.", sentiment: "peaceful" },
  ]);   const [showAddEntry, setShowAddEntry] = useState(false);
  const [newEntry, setNewEntry] = useState({ text: "", sentiment: "grateful" as Sentiment });   const [completedDays, setCompletedDays] = useState<Set<number>>(new Set([15, 16, 17, 18, 19, 20, 21]));   const [missedDays, setMissedDays] = useState<Set<number>>(new Set([12, 13, 14]));
  const [sessionStats, setSessionStats] = useState<SessionStats[]>([]);   useEffect(() => {     const savedEntries = localStorage.getItem("journalEntries");     const savedCompleted = localStorage.getItem("completedDays");     const savedMissed = localStorage.getItem("missedDays");     const savedStats = localStorage.getItem("yogaSessionStats");
    if (savedEntries) {
      setJournalEntries(JSON.parse(savedEntries));     }
    if (savedCompleted) {       setCompletedDays(new Set(JSON.parse(savedCompleted)));     }
    if (savedMissed) {       setMissedDays(new Set(JSON.parse(savedMissed)));
    }
    if (savedStats) {       setSessionStats(JSON.parse(savedStats));     }   }, []);   useEffect(() => {     const timeoutId = setTimeout(() => {       localStorage.setItem("journalEntries", JSON.stringify(journalEntries));
      localStorage.setItem("completedDays", JSON.stringify(Array.from(completedDays)));
      localStorage.setItem("missedDays", JSON.stringify(Array.from(missedDays)));
    }, 300);     return () => clearTimeout(timeoutId);   }, [journalEntries, completedDays, missedDays]);
  const handleAddEntry = useCallback(() => {     if (newEntry.text.trim()) {
      const today = new Date();
      const dateStr = today.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });       const entry: JournalEntry = {         id: Date.now().toString(),         date: dateStr,         entry: newEntry.text,         sentiment: newEntry.sentiment,
      };       setJournalEntries(prev => [entry, ...prev]);       setNewEntry({ text: "", sentiment: "grateful" });       setShowAddEntry(false);     }
  }, [newEntry]);
  const getSentimentIcon = useCallback((sentiment: Sentiment) => {     switch (sentiment) {       case "happy": return <Smile className="w-4 h-4" />;       case "grateful": return <Heart className="w-4 h-4" />;
      case "peaceful": return <Heart className="w-4 h-4" />;       case "reflective": return <Meh className="w-4 h-4" />;
      case "neutral": return <Meh className="w-4 h-4" />;     }   }, []);   const getSentimentColor = useCallback((sentiment: Sentiment) => {     switch (sentiment) {
      case "happy": return "text-yellow-300";       case "grateful": return "text-pink-300";       case "peaceful": return "text-blue-300";
      case "reflective": return "text-purple-300";       case "neutral": return "text-gray-300";
    }   }, []);
  if (view === null) {     return (
      <div className="fixed inset-0">         <div           className="absolute inset-0 bg-cover bg-center animate-fade-in"           style={{ backgroundImage: `url(${meditationBg})` }}         >
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-yoga-start))]/40 to-black/50" />         </div>
        <Button
          variant="ghost"
          onClick={() => navigate("/menu")}           className="absolute top-6 left-6 text-white hover:bg-white/10 z-10"         >           <ArrowLeft className="mr-2 h-4 w-4" />           Back
        </Button>         <div className="relative h-full flex flex-col items-center justify-center px-8 pb-24">
          <h1 className="text-6xl font-light text-white mb-16 animate-fade-in-up">             Your Progress
          </h1>           <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl w-full">
            <div
              onClick={() => setView("calendar")}               className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-yoga-start))]/30 to-[hsl(var(--gradient-yoga-end))]/30                 backdrop-blur-sm border border-white/20 cursor-pointer                 transition-all duration-500 hover:scale-105 hover:shadow-2xl                 animate-fade-in-up"
              style={{ animationDelay: '0.1s' }}             >               <Calendar className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />               <h2 className="text-3xl font-light text-white mb-4">Calendar</h2>               <p className="text-white/70 font-light leading-relaxed">                 View your practice history and progress over time
              </p>
            </div>             <div
              onClick={() => setView("journal")}               className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-meditation-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30
                backdrop-blur-sm border border-white/20 cursor-pointer                 transition-all duration-500 hover:scale-105 hover:shadow-2xl                 animate-fade-in-up"               style={{ animationDelay: '0.2s' }}             >               <BookOpen className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />               <h2 className="text-3xl font-light text-white mb-4">Gratitude Journal</h2>               <p className="text-white/70 font-light leading-relaxed">
                Reflect on your daily gratitude and mindfulness               </p>
            </div>             <div               onClick={() => setView("stats")}               className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-community-start))]/30 to-[hsl(var(--gradient-community-end))]/30                 backdrop-blur-sm border border-white/20 cursor-pointer
                transition-all duration-500 hover:scale-105 hover:shadow-2xl
                animate-fade-in-up"               style={{ animationDelay: '0.3s' }}
            >
              <BarChart3 className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />               <h2 className="text-3xl font-light text-white mb-4">Statistics</h2>               <p className="text-white/70 font-light leading-relaxed">                 Overall statistics and insights about your journey
              </p>             </div>             <div               onClick={() => setView("body")}               className="group relative p-8 rounded-3xl bg-gradient-to-br from-[hsl(var(--gradient-yoga-start))]/30 to-[hsl(var(--gradient-meditation-end))]/30                 backdrop-blur-sm border border-white/20 cursor-pointer                 transition-all duration-500 hover:scale-105 hover:shadow-2xl                 animate-fade-in-up"               style={{ animationDelay: '0.4s' }}             >               <Activity className="w-12 h-12 text-white mb-4 grayscale group-hover:grayscale-0 transition-all duration-500" />               <h2 className="text-3xl font-light text-white mb-4">Body Progression</h2>               <p className="text-white/70 font-light leading-relaxed">
                Track your physical progress and transformations
              </p>             </div>           </div>
        </div>
        {}         <div className="absolute bottom-0 left-0 right-0 bg-black/70 border-t border-white/10 px-8 py-4 z-20">           <div className="max-w-6xl mx-auto flex items-center justify-around">
            <button               onClick={() => setView("calendar")}               className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors"             >               <Calendar className="w-6 h-6" />               <span className="text-xs font-light">Calendar</span>             </button>
            <button
              onClick={() => setView("journal")}               className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors"             >               <BookOpen className="w-6 h-6" />
              <span className="text-xs font-light">Journal</span>             </button>             <button               onClick={() => setView("stats")}               className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors"             >               <BarChart3 className="w-6 h-6" />               <span className="text-xs font-light">Stats</span>             </button>             <button               onClick={() => setView("body")}               className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors"             >
              <Activity className="w-6 h-6" />               <span className="text-xs font-light">Body</span>
            </button>             <button
              onClick={() => navigate("/menu")}               className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-colors"             >               <Menu className="w-6 h-6" />
              <span className="text-xs font-light">Menu</span>
            </button>           </div>         </div>         <div className="absolute top-20 right-20 w-48 h-48 rounded-full bg-white/5 animate-pulse-slow" />
        <div className="absolute bottom-24 left-20 w-64 h-64 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '1.5s' }} />       </div>     );
  }
  const renderView = () => {     switch (view) {       case "calendar":         return (           <div className="text-center animate-fade-in">             <h2 className="text-4xl font-light text-white mb-8 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>Calendar View</h2>             <div className="grid grid-cols-7 gap-2 max-w-2xl mx-auto bg-black/50 rounded-2xl p-6 border border-white/20 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>               {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (                 <div key={day} className="text-white/70 text-sm font-light py-2">{day}</div>               ))}               {Array.from({ length: 35 }).map((_, i) => {                 const dayNum = i - 6;
                const isCompleted = completedDays.has(dayNum);                 const isMissed = missedDays.has(dayNum);                 const isValidDay = dayNum > 0 && dayNum <= 31;                 const handleDayClick = () => {
                  if (!isValidDay) return;
                  const newCompleted = new Set(completedDays);                   const newMissed = new Set(missedDays);                   if (isCompleted) {
                    newCompleted.delete(dayNum);
                    newMissed.add(dayNum);
                    setCompletedDays(newCompleted);                     setMissedDays(newMissed);
                  } else if (isMissed) {
                    newMissed.delete(dayNum);                     setMissedDays(newMissed);                   } else {                     newCompleted.add(dayNum);                     setCompletedDays(newCompleted);                   }                 };                 return (                   <div                     key={i}                     className={`aspect-square rounded-lg border flex items-center justify-center text-sm font-light                       ${i < 7 || i > 27 ? 'opacity-0 pointer-events-none' : ''}                       ${isCompleted                         ? 'bg-green-500/60 border-green-400/50 text-white shadow-lg shadow-green-500/20'                         : isMissed                         ? 'bg-red-500/40 border-red-400/40 text-white/80'                         : i % 7 === 0 || i % 7 === 6
                          ? 'bg-white/20 border-white/20 text-white/60'                           : 'bg-white/30 border-white/25 text-white/70'                       }                       ${isValidDay ? 'cursor-pointer' : ''}`}                     style={{                       transition: 'background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease',
                    }}                     onClick={handleDayClick}
                    onMouseEnter={(e) => {                       if (isValidDay) {                         e.currentTarget.style.transform = 'scale(1.05)';                         e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.4)';                       }                     }}                     onMouseLeave={(e) => {                       if (isValidDay) {                         e.currentTarget.style.transform = 'scale(1)';                         e.currentTarget.style.borderColor = '';                       }
                    }}                   >                     {i < 7 || i > 27 ? "" : dayNum}
                  </div>                 );               })}
            </div>             <div className="flex items-center justify-center gap-6 mt-8 text-sm animate-fade-in-up" style={{ animationDelay: '0.3s' }}>               <div className="flex items-center gap-2">                 <div className="w-4 h-4 rounded bg-green-500/60 border border-green-400/50" />
                <span className="text-white/70 font-light">Completed</span>
              </div>               <div className="flex items-center gap-2">                 <div className="w-4 h-4 rounded bg-red-500/40 border border-red-400/40" />
                <span className="text-white/70 font-light">Missed</span>
              </div>               <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-white/30 border border-white/25" />
                <span className="text-white/70 font-light">Regular</span>
              </div>             </div>
            <p className="text-white/60 text-sm mt-4 font-light animate-fade-in-up" style={{ animationDelay: '0.4s' }}>               Tap days to mark as completed or missed.             </p>           </div>         );       case "journal":         return (           <div className="max-w-2xl mx-auto w-full">             <h2 className="text-4xl font-light text-white mb-8 text-center">Gratitude Journal</h2>             <div className="space-y-6">               {journalEntries.map((entry) => (                 <div                   key={entry.id}                   className="p-6 rounded-2xl bg-white/10 border border-white/20 hover:bg-white/15 transition-all duration-300"                 >
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-white/60 text-sm font-light">{entry.date}</div>
                    <div className={`${getSentimentColor(entry.sentiment)} flex items-center gap-1`}>
                      {getSentimentIcon(entry.sentiment)}                       <span className="text-xs capitalize">{entry.sentiment}</span>                     </div>                   </div>                   <p className="text-white/90 font-light leading-relaxed">{entry.entry}</p>
                </div>               ))}               <button                 onClick={() => setShowAddEntry(true)}
                className="w-full p-6 rounded-2xl bg-white/10 border border-white/20 hover:bg-white/15 transition-all duration-300 text-white/70 hover:text-white text-center font-light"               >                 + Add New Entry               </button>             </div>
            {}             {showAddEntry && (               <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70">                 <div className="bg-black/90 rounded-2xl border border-white/20 p-8 max-w-lg w-full max-h-[80vh] overflow-y-auto">                   <div className="flex items-center justify-between mb-6">                     <h3 className="text-2xl font-light text-white">New Journal Entry</h3>                     <button                       onClick={() => {
                        setShowAddEntry(false);                         setNewEntry({ text: "", sentiment: "grateful" });                       }}
                      className="text-white/60 hover:text-white transition-colors"                     >                       <X className="w-5 h-5" />
                    </button>
                  </div>                   <div className="space-y-6">                     <div>                       <label className="block text-white/70 text-sm font-light mb-3">                         How are you feeling today?                       </label>                       <div className="grid grid-cols-2 gap-3">                         {(["happy", "grateful", "peaceful", "neutral", "reflective"] as Sentiment[]).map((sentiment) => (                           <button                             key={sentiment}                             onClick={() => setNewEntry({ ...newEntry, sentiment })}
                            className={`p-4 rounded-xl border transition-all duration-300 flex items-center justify-center gap-2                               ${newEntry.sentiment === sentiment
                                ? `bg-white/20 border-white/40 ${getSentimentColor(sentiment)}`                                 : 'bg-white/10 border-white/20 text-white/60 hover:bg-white/15 hover:border-white/30'                               }`}                           >                             {getSentimentIcon(sentiment)}                             <span className="capitalize font-light text-sm">{sentiment}</span>
                          </button>                         ))}
                      </div>                     </div>                     <div>                       <label className="block text-white/70 text-sm font-light mb-3">
                        What are you grateful for today?                       </label>
                      <textarea                         value={newEntry.text}                         onChange={(e) => setNewEntry({ ...newEntry, text: e.target.value })}
                        placeholder="Write your thoughts here..."                         className="w-full p-4 rounded-xl bg-white/10 border border-white/20 text-white placeholder-white/40 font-light leading-relaxed resize-none focus:outline-none focus:border-white/40 focus:bg-white/15 transition-all duration-300"                         rows={5}                       />                     </div>
                    <Button                       onClick={handleAddEntry}
                      disabled={!newEntry.text.trim()}                       className="w-full bg-white/20 hover:bg-white/30 text-white border border-white/30 disabled:opacity-50 disabled:cursor-not-allowed"                       size="lg"
                    >                       Save Entry                     </Button>
                  </div>                 </div>               </div>             )}           </div>
        );       case "stats":
        const totalSessions = sessionStats.length;         const totalTimeMinutes = sessionStats.reduce((sum, stat) => sum + (stat.sessionDuration || 0) / 60, 0);
        const totalTimeHours = Math.floor(totalTimeMinutes / 60);         const totalTimeMinutesRemainder = Math.floor(totalTimeMinutes % 60);
        const avgAccuracy = sessionStats.length > 0
          ? sessionStats.reduce((sum, stat) => sum + (stat.accuracyScore || 0), 0) / sessionStats.length
          : 0;         const avgFormScore = sessionStats.length > 0
          ? sessionStats.reduce((sum, stat) => sum + (stat.avgFormScore || 0), 0) / sessionStats.length           : 0;         const totalReps = sessionStats.reduce((sum, stat) => sum + (stat.repCount || 0), 0);         const totalPoseEntries = sessionStats.reduce((sum, stat) => sum + (stat.poseEntries || 0), 0);         const today = new Date();         today.setHours(0, 0, 0, 0);
        let streak = 0;         let checkDate = new Date(today);         const sessionDates = new Set(           sessionStats.map(stat => {
            const date = new Date(stat.timestamp);
            date.setHours(0, 0, 0, 0);
            return date.getTime();           })         );         while (sessionDates.has(checkDate.getTime())) {           streak++;           checkDate.setDate(checkDate.getDate() - 1);         }         const weekAgo = new Date();         weekAgo.setDate(weekAgo.getDate() - 7);         const recentSessions = sessionStats.filter(stat => new Date(stat.timestamp) >= weekAgo);         return (           <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-light text-white mb-8 text-center">Overall Statistics</h2>             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">               <div className="p-8 rounded-2xl bg-white/10 border border-white/20 text-center">                 <div className="text-5xl font-light text-white mb-2">{totalSessions}</div>                 <div className="text-white/70 font-light">Total Sessions</div>               </div>
              <div className="p-8 rounded-2xl bg-white/10 border border-white/20 text-center">
                <div className="text-5xl font-light text-white mb-2">
                  {totalTimeHours > 0 ? `${totalTimeHours}h` : ''}                   {totalTimeMinutesRemainder > 0 ? `${totalTimeMinutesRemainder}m` : totalTimeHours === 0 ? '0m' : ''}
                </div>                 <div className="text-white/70 font-light">Time Practiced</div>
              </div>
              <div className="p-8 rounded-2xl bg-white/10 border border-white/20 text-center">                 <div className="text-5xl font-light text-white mb-2">{streak}</div>                 <div className="text-white/70 font-light">Day Streak</div>               </div>             </div>             <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">               <div className="p-8 rounded-2xl bg-white/10 border border-white/20">
                <h3 className="text-2xl font-light text-white mb-6">Performance</h3>                 <div className="space-y-4">                   <div className="flex items-center justify-between">                     <span className="text-white/80 font-light">Avg Accuracy</span>
                    <span className="text-white text-xl font-light">{Math.round(avgAccuracy)}%</span>
                  </div>                   <div className="flex items-center justify-between">
                    <span className="text-white/80 font-light">Avg Form Score</span>
                    <span className="text-white text-xl font-light">{Math.round(avgFormScore)}%</span>                   </div>
                  <div className="flex items-center justify-between">                     <span className="text-white/80 font-light">Total Reps</span>                     <span className="text-white text-xl font-light">{totalReps}</span>                   </div>                   <div className="flex items-center justify-between">                     <span className="text-white/80 font-light">Poses Completed</span>                     <span className="text-white text-xl font-light">{totalPoseEntries}</span>                   </div>                 </div>               </div>               <div className="p-8 rounded-2xl bg-white/10 border border-white/20">
                <h3 className="text-2xl font-light text-white mb-6">Recent Sessions</h3>                 <div className="space-y-3 max-h-64 overflow-y-auto">
                  {recentSessions.length > 0 ? (                     recentSessions.slice(0, 5).map((stat, i) => {                       const date = new Date(stat.timestamp);                       const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });                       return (                         <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/10">
                          <div className="flex items-center justify-between mb-2">                             <span className="text-white/80 font-light text-sm">{dateStr}</span>                             <span className="text-white/60 font-light text-xs">{Math.round(stat.sessionDuration / 60)}min</span>
                          </div>                           <div className="flex items-center gap-4 text-xs text-white/70">                             <span>Accuracy: {Math.round(stat.accuracyScore || 0)}%</span>                             <span>Reps: {stat.repCount || 0}</span>                           </div>
                        </div>
                      );                     })                   ) : (                     <div className="text-white/60 font-light text-center py-8">No recent sessions</div>                   )}                 </div>
              </div>             </div>           </div>         );       case "body":
        return (           <div className="max-w-2xl mx-auto">
            <h2 className="text-4xl font-light text-white mb-8 text-center">Body Progression</h2>             <div className="space-y-6">               <div className="p-6 rounded-2xl bg-white/10 border border-white/20">                 <h3 className="text-2xl font-light text-white mb-4">Flexibility</h3>
                <div className="space-y-3">                   <div className="flex items-center justify-between">
                    <span className="text-white/80 font-light">Forward Fold</span>
                    <div className="flex-1 mx-4 h-2 bg-white/10 rounded-full overflow-hidden">                       <div className="h-full bg-gradient-to-r from-[hsl(var(--gradient-yoga-start))] to-[hsl(var(--gradient-yoga-end))] rounded-full" style={{ width: '75%' }} />                     </div>                     <span className="text-white/60 text-sm">75%</span>                   </div>                   <div className="flex items-center justify-between">                     <span className="text-white/80 font-light">Shoulder Mobility</span>                     <div className="flex-1 mx-4 h-2 bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-[hsl(var(--gradient-yoga-start))] to-[hsl(var(--gradient-yoga-end))] rounded-full" style={{ width: '60%' }} />                     </div>                     <span className="text-white/60 text-sm">60%</span>                   </div>                 </div>
              </div>
              <div className="p-6 rounded-2xl bg-white/10 border border-white/20">                 <h3 className="text-2xl font-light text-white mb-4">Strength</h3>
                <div className="space-y-3">                   <div className="flex items-center justify-between">                     <span className="text-white/80 font-light">Core Stability</span>                     <div className="flex-1 mx-4 h-2 bg-white/10 rounded-full overflow-hidden">                       <div className="h-full bg-gradient-to-r from-[hsl(var(--gradient-meditation-start))] to-[hsl(var(--gradient-meditation-end))] rounded-full" style={{ width: '80%' }} />
                    </div>                     <span className="text-white/60 text-sm">80%</span>                   </div>
                  <div className="flex items-center justify-between">
                    <span className="text-white/80 font-light">Balance</span>                     <div className="flex-1 mx-4 h-2 bg-white/10 rounded-full overflow-hidden">                       <div className="h-full bg-gradient-to-r from-[hsl(var(--gradient-meditation-start))] to-[hsl(var(--gradient-meditation-end))] rounded-full" style={{ width: '70%' }} />                     </div>                     <span className="text-white/60 text-sm">70%</span>
                  </div>                 </div>               </div>
              <div className="p-6 rounded-2xl bg-white/10 border border-white/20">                 <h3 className="text-2xl font-light text-white mb-4">Recent Achievements</h3>
                <div className="space-y-3 text-white/80 font-light">                   <div>✓ Completed 7-day meditation streak</div>                   <div>✓ Held plank pose for 60 seconds</div>
                  <div>✓ Improved flexibility by 15%</div>                 </div>
              </div>             </div>           </div>
        );
    }
  };
  return (     <div className="fixed inset-0">       <div         className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${meditationBg})` }}
      >         <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-[hsl(var(--gradient-yoga-start))]/40 to-black/50" />       </div>         <Button
          variant="ghost"
          onClick={() => setView(null)}           className="absolute top-6 left-6 text-white hover:bg-white/10 z-10"
        >         <ArrowLeft className="mr-2 h-4 w-4" />         Back       </Button>       <div className="relative h-full flex flex-col items-center justify-center px-8 pb-24 overflow-y-auto">         {renderView()}
      </div>       {}       <div className="absolute bottom-0 left-0 right-0 bg-black/70 border-t border-white/10 px-8 py-4 z-20">
        <div className="max-w-6xl mx-auto flex items-center justify-around">           <button
            onClick={() => setView("calendar")}             className={`flex flex-col items-center gap-2 transition-all duration-200 ${view === "calendar" ? "text-white" : "text-white/70 hover:text-white"}`}
            style={{ transition: 'color 0.2s ease, transform 0.2s ease' }}           >
            <Calendar className="w-6 h-6" style={{ transition: 'transform 0.2s ease' }} />
            <span className="text-xs font-light">Calendar</span>           </button>
          <button             onClick={() => setView("journal")}             className={`flex flex-col items-center gap-2 transition-all duration-200 ${view === "journal" ? "text-white" : "text-white/70 hover:text-white"}`}             style={{ transition: 'color 0.2s ease, transform 0.2s ease' }}
          >
            <BookOpen className="w-6 h-6" style={{ transition: 'transform 0.2s ease' }} />             <span className="text-xs font-light">Journal</span>           </button>           <button             onClick={() => setView("stats")}
            className={`flex flex-col items-center gap-2 transition-all duration-200 ${view === "stats" ? "text-white" : "text-white/70 hover:text-white"}`}
            style={{ transition: 'color 0.2s ease, transform 0.2s ease' }}           >
            <BarChart3 className="w-6 h-6" style={{ transition: 'transform 0.2s ease' }} />
            <span className="text-xs font-light">Stats</span>           </button>
          <button             onClick={() => setView("body")}             className={`flex flex-col items-center gap-2 transition-all duration-200 ${view === "body" ? "text-white" : "text-white/70 hover:text-white"}`}
            style={{ transition: 'color 0.2s ease, transform 0.2s ease' }}
          >
            <Activity className="w-6 h-6" style={{ transition: 'transform 0.2s ease' }} />             <span className="text-xs font-light">Body</span>           </button>
          <button             onClick={() => navigate("/menu")}             className="flex flex-col items-center gap-2 text-white/70 hover:text-white transition-all duration-200"             style={{ transition: 'color 0.2s ease, transform 0.2s ease' }}           >             <Menu className="w-6 h-6" style={{ transition: 'transform 0.2s ease' }} />
            <span className="text-xs font-light">Menu</span>           </button>         </div>       </div>       <div className="absolute top-20 right-20 w-48 h-48 rounded-full bg-white/5 animate-pulse-slow" />       <div className="absolute bottom-24 left-20 w-64 h-64 rounded-full bg-white/5 animate-pulse-slow" style={{ animationDelay: '1.5s' }} />     </div>   ); };
export default ProgressPage; 