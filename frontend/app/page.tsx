'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col items-center justify-center p-6 font-sans">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-[400px] bg-indigo-500/10 blur-[120px] rounded-full" />

      <div className="z-10 text-center space-y-12 max-w-5xl">
        <div className="space-y-4">
          <h1 className="text-6xl font-bold text-white tracking-tight">
            AURALIS<span className="text-indigo-500">.</span>
          </h1>
          <p className="text-slate-300 max-w-2xl mx-auto text-xl">
            Voice-First Enterprise Intelligence Layer. Build autonomous voice agents with visual workflows.
          </p>
        </div>

        <div className="flex gap-4 justify-center">
          <Link
            href="/workflow-editor"
            className="px-8 py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold text-lg transition-all shadow-xl hover:shadow-2xl hover:scale-105"
          >
            Launch Workflow Editor
          </Link>
          <Link
            href="/graph-explorer"
            className="px-8 py-4 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold text-lg transition-all shadow-xl hover:shadow-2xl hover:scale-105"
          >
            Explore Knowledge Graph
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left pt-12 border-t border-white/10">
          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all">
            <h3 className="text-indigo-400 font-bold text-sm uppercase mb-3">Visual Workflow Builder</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Drag-and-drop interface for building complex voice agent workflows. No code required.
            </p>
          </div>
          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all">
            <h3 className="text-indigo-400 font-bold text-sm uppercase mb-3">Knowledge Graph RAG</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Real-time Qdrant vector search with Neo4j graph relationships for contextual intelligence.
            </p>
          </div>
          <div className="p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm hover:bg-white/10 transition-all">
            <h3 className="text-indigo-400 font-bold text-sm uppercase mb-3">Multi-Tenant SaaS</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Enterprise-grade isolation with Clerk auth, PostgreSQL, and company-scoped data.
            </p>
          </div>
        </div>

        <div className="pt-8 text-slate-400 text-sm">
          <p>Powered by Gemini 2.5 Flash • Optimized for sub-800ms response</p>
        </div>
      </div>
    </main>
  );
}