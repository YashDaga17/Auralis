"use client";
import Vapi from "@vapi-ai/web";
import { useState, useEffect } from "react";
import { Mic, MicOff, Zap } from "lucide-react";

// Initialize Vapi with your Public Key from .env.local
const vapi = new Vapi(process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY!);

export default function AuralisButton() {
  const [isCalling, setIsCalling] = useState(false);

  const toggleCall = () => {
    if (isCalling) {
      vapi.stop();
    } else {
      vapi.start(process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID!);
    }
  };

  useEffect(() => {
    vapi.on("call-start", () => setIsCalling(true));
    vapi.on("call-end", () => setIsCalling(false));
    vapi.on("error", (e) => console.error(e));
  }, []);

  return (
    <div className="flex flex-col items-center gap-4">
      <button 
        onClick={toggleCall}
        className={`relative p-8 rounded-full transition-all duration-500 ${
          isCalling 
          ? 'bg-red-500 shadow-[0_0_40px_rgba(239,68,68,0.6)]' 
          : 'bg-indigo-600 hover:bg-indigo-500 shadow-xl'
        }`}
      >
        {isCalling ? (
          <MicOff className="w-12 h-12 text-white" />
        ) : (
          <Mic className="w-12 h-12 text-white" />
        )}
        
        {isCalling && (
          <span className="absolute inset-0 rounded-full border-4 border-white/30 animate-ping" />
        )}
      </button>
      
      <p className="text-sm font-medium text-slate-400 uppercase tracking-widest flex items-center gap-2">
        <Zap className={`w-4 h-4 ${isCalling ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'}`} />
        {isCalling ? "Auralis is Live" : "Start Voice Session"}
      </p>
    </div>
  );
}