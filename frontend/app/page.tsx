import AuralisButton from "@/components/AuralisButton";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0a0b] flex flex-col items-center justify-center p-6 font-sans">
      {/* Background Glow Effect */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-[400px] bg-indigo-500/10 blur-[120px] rounded-full" />

      {/* Navigation */}
      <nav className="absolute top-6 right-6 z-20">
        <Link
          href="/workflow-editor"
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors shadow-lg"
        >
          🎨 Workflow Editor
        </Link>
      </nav>

      <div className="z-10 text-center space-y-12">
        <div className="space-y-4">
          <h1 className="text-5xl font-bold text-white tracking-tight">
            AURALIS<span className="text-indigo-500">.</span>
          </h1>
          <p className="text-slate-400 max-w-md mx-auto text-lg">
            Voice-First Enterprise Intelligence Layer. Orchestrating chaos through autonomous conversation.
          </p>
        </div>

        <div className="py-12">
          <AuralisButton />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left max-w-4xl pt-12 border-t border-white/5">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h3 className="text-indigo-400 font-bold text-xs uppercase mb-2">Memory</h3>
            <p className="text-slate-300 text-sm">Real-time Qdrant RAG sync active.</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h3 className="text-indigo-400 font-bold text-xs uppercase mb-2">Inference</h3>
            <p className="text-slate-300 text-sm">Running on Auralis Chaos Engine.</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <h3 className="text-indigo-400 font-bold text-xs uppercase mb-2">Latency</h3>
            <p className="text-slate-300 text-sm">Optimized for &lt;800ms response.</p>
          </div>
        </div>
      </div>
    </main>
  );
}