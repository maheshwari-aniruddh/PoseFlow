import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Plus, MessageCircle, Heart, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import meditationBg from "@/assets/meditation-silhouette.jpg";

interface CommunityPost {
  id: string;
  type: "story" | "bridge" | "reddit";
  name?: string;
  who?: string;
  author?: string;
  text: string;
  timestamp: number;
  upvotes?: number;
  subreddit?: string;
}

const CommunityPage = () => {
  const navigate = useNavigate();
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [showStoryForm, setShowStoryForm] = useState(false);
  const [showBridgeForm, setShowBridgeForm] = useState(false);
  const [storyName, setStoryName] = useState("");
  const [storyText, setStoryText] = useState("");
  const [bridgeWho, setBridgeWho] = useState("");
  const [bridgeWhat, setBridgeWhat] = useState("");
  const [loadingReddit, setLoadingReddit] = useState(false);

  // Load posts from localStorage
  useEffect(() => {
    loadPosts();
    // Load Reddit posts on mount
    loadRedditPosts();
  }, []);

  const loadPosts = () => {
    try {
      const raw = localStorage.getItem("communityPosts");
      if (raw) {
        const savedPosts = JSON.parse(raw);
        setPosts(savedPosts);
      }
    } catch (e) {
      console.error("Error loading posts", e);
    }
  };

  const savePosts = (newPosts: CommunityPost[]) => {
    try {
      localStorage.setItem("communityPosts", JSON.stringify(newPosts));
      setPosts(newPosts);
    } catch (e) {
      console.error("Error saving posts", e);
    }
  };

  const loadRedditPosts = async () => {
    setLoadingReddit(true);
    try {
      // Fetch from multiple subreddits to get more posts
      const subreddits = ['meditation', 'yoga', 'mindfulness', 'mindful', 'ZenHabits', 'Buddhism'];
      let allRedditPosts: CommunityPost[] = [];
      
      // Fetch from each subreddit
      for (const subreddit of subreddits) {
        try {
          const response = await fetch(`https://www.reddit.com/r/${subreddit}/hot.json?limit=25`);
          const data = await response.json();
          
          const redditPosts: CommunityPost[] = data.data.children
            .filter((child: any) => child.data.selftext && child.data.selftext.length > 30)
            .map((child: any) => ({
              id: `reddit_${child.data.id}`,
              type: "reddit" as const,
              author: child.data.author,
              text: child.data.selftext.substring(0, 500) + (child.data.selftext.length > 500 ? "..." : ""),
              timestamp: child.data.created_utc * 1000,
              upvotes: child.data.ups,
              subreddit: child.data.subreddit,
            }));
          
          allRedditPosts = [...allRedditPosts, ...redditPosts];
        } catch (subError) {
          console.error(`Error loading from r/${subreddit}:`, subError);
          // Continue with other subreddits
        }
      }

      // Merge with existing posts, avoiding duplicates
      const existingIds = new Set(posts.map(p => p.id));
      const newRedditPosts = allRedditPosts.filter(p => !existingIds.has(p.id));
      
      if (newRedditPosts.length > 0) {
        const allPosts = [...posts, ...newRedditPosts].sort((a, b) => b.timestamp - a.timestamp);
        savePosts(allPosts);
      }
    } catch (error) {
      console.error("Error loading Reddit posts:", error);
    } finally {
      setLoadingReddit(false);
    }
  };

  const submitStory = () => {
    if (!storyText.trim()) return;

    const newPost: CommunityPost = {
      id: `story_${Date.now()}`,
      type: "story",
      name: storyName.trim() || "Anonymous",
      text: storyText.trim(),
      timestamp: Date.now(),
    };

    const updatedPosts = [newPost, ...posts];
    savePosts(updatedPosts);
    setStoryName("");
    setStoryText("");
    setShowStoryForm(false);
  };

  const submitBridge = () => {
    if (!bridgeWhat.trim()) return;

    const newPost: CommunityPost = {
      id: `bridge_${Date.now()}`,
      type: "bridge",
      who: bridgeWho.trim() || "Someone",
      text: bridgeWhat.trim(),
      timestamp: Date.now(),
    };

    const updatedPosts = [newPost, ...posts];
    savePosts(updatedPosts);
    setBridgeWho("");
    setBridgeWhat("");
    setShowBridgeForm(false);
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const getPostLabel = (post: CommunityPost) => {
    switch (post.type) {
      case "story":
        return "Breath Story";
      case "bridge":
        return "Yoga Bridge";
      case "reddit":
        return "From r/meditation";
      default:
        return "Post";
    }
  };

  const getPostAuthor = (post: CommunityPost) => {
    if (post.type === "reddit") return post.author || "Redditor";
    if (post.type === "bridge") return post.who || "Someone";
    return post.name || "Anonymous";
  };

  // Sort posts and limit to 40 most recent
  const sortedPosts = [...posts]
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, 40); // Show up to 40 posts

  return (
    <div className="fixed inset-0 overflow-y-auto">
      {/* Background */}
      <div
        className="fixed inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${meditationBg})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-[hsl(var(--gradient-community-start))]/50 to-black/60" />
      </div>

      {/* Header */}
      <div className="relative z-10 p-6 flex justify-between items-center">
        <Button
          variant="ghost"
          onClick={() => navigate("/menu")}
          className="text-white hover:bg-white/10"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className="flex gap-3">
          <Button
            onClick={() => setShowStoryForm(!showStoryForm)}
            className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
          >
            <Plus className="mr-2 h-4 w-4" />
            Share Story
          </Button>
          <Button
            onClick={() => setShowBridgeForm(!showBridgeForm)}
            className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
          >
            <Plus className="mr-2 h-4 w-4" />
            Yoga Bridge
          </Button>
          <Button
            onClick={loadRedditPosts}
            disabled={loadingReddit}
            className="bg-white/20 hover:bg-white/30 text-white border border-white/30"
          >
            {loadingReddit ? "Loading..." : "Refresh"}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 pb-12">
        <h1 className="text-6xl font-light text-white mb-8 text-center">Community Wall</h1>

        {/* Story Form */}
        {showStoryForm && (
          <div className="mb-6 bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
            <h3 className="text-2xl font-light text-white mb-4">Share Your Breath Story</h3>
            <input
              type="text"
              placeholder="Your name (optional)"
              value={storyName}
              onChange={(e) => setStoryName(e.target.value)}
              className="w-full mb-4 bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
            />
            <textarea
              placeholder="Share how a breath changed your mood..."
              value={storyText}
              onChange={(e) => setStoryText(e.target.value)}
              maxLength={200}
              className="w-full mb-4 bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 min-h-[100px]"
            />
            <div className="flex justify-between items-center">
              <span className="text-white/60 text-sm">{storyText.length} / 200</span>
              <div className="flex gap-3">
                <Button
                  onClick={() => setShowStoryForm(false)}
                  className="bg-white/10 hover:bg-white/20 text-white"
                >
                  Cancel
                </Button>
                <Button
                  onClick={submitStory}
                  className="bg-white/20 hover:bg-white/30 text-white"
                >
                  Post Story
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Bridge Form */}
        {showBridgeForm && (
          <div className="mb-6 bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
            <h3 className="text-2xl font-light text-white mb-4">Log a Yoga Bridge</h3>
            <input
              type="text"
              placeholder="Who was with you? (optional)"
              value={bridgeWho}
              onChange={(e) => setBridgeWho(e.target.value)}
              className="w-full mb-4 bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50"
            />
            <textarea
              placeholder="Describe the moment..."
              value={bridgeWhat}
              onChange={(e) => setBridgeWhat(e.target.value)}
              className="w-full mb-4 bg-white/10 border border-white/30 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 min-h-[100px]"
            />
            <div className="flex justify-end gap-3">
              <Button
                onClick={() => setShowBridgeForm(false)}
                className="bg-white/10 hover:bg-white/20 text-white"
              >
                Cancel
              </Button>
              <Button
                onClick={submitBridge}
                className="bg-white/20 hover:bg-white/30 text-white"
              >
                Post Bridge
              </Button>
            </div>
          </div>
        )}

        {/* Posts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedPosts.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-white/60 text-xl">No posts yet. Be the first to share!</p>
            </div>
          ) : (
            sortedPosts.map((post) => (
              <div
                key={post.id}
                className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-[#9ba3ff] uppercase tracking-wider">
                    {getPostLabel(post)}
                  </span>
                  {post.type === "reddit" && post.upvotes && (
                    <div className="flex items-center gap-1 text-white/60 text-sm">
                      <Heart className="h-3 w-3" />
                      {post.upvotes}
                    </div>
                  )}
                </div>

                <h3 className="text-white font-semibold mb-3">{getPostAuthor(post)}</h3>

                <p className="text-white/80 text-sm mb-4 leading-relaxed whitespace-pre-wrap">
                  {post.text}
                </p>

                <div className="flex items-center justify-between text-xs text-white/50">
                  <span>{formatDate(post.timestamp)}</span>
                  {post.type === "reddit" && (
                    <span className="text-[#9ba3ff]">r/{post.subreddit}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Decorative circles */}
      <div className="fixed top-1/4 left-1/4 w-48 h-48 rounded-full bg-white/5 animate-pulse-slow pointer-events-none" />
      <div className="fixed bottom-1/4 right-1/4 w-64 h-64 rounded-full bg-white/5 animate-pulse-slow pointer-events-none" style={{ animationDelay: '1.5s' }} />
    </div>
  );
};

export default CommunityPage;
