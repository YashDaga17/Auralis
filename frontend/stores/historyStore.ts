import { create } from 'zustand';
import { WorkflowNode, WorkflowEdge } from './workflowStore';

interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

interface HistoryState {
  past: WorkflowState[];
  present: WorkflowState | null;
  future: WorkflowState[];
  maxHistorySize: number;
  
  // History operations
  recordState: (state: WorkflowState) => void;
  undo: () => WorkflowState | null;
  redo: () => WorkflowState | null;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clearHistory: () => void;
  setMaxHistorySize: (size: number) => void;
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  past: [],
  present: null,
  future: [],
  maxHistorySize: 50, // Limit history to prevent memory issues

  // Record a new state
  recordState: (state) => {
    set((current) => {
      const newPast = [...current.past];
      
      // Add current present to past if it exists
      if (current.present) {
        newPast.push(current.present);
      }

      // Limit history size
      const { maxHistorySize } = get();
      if (newPast.length > maxHistorySize) {
        newPast.shift(); // Remove oldest state
      }

      return {
        past: newPast,
        present: state,
        future: [], // Clear future when new action is recorded
      };
    });
  },

  // Undo to previous state
  undo: () => {
    const { past, present } = get();
    
    if (past.length === 0) {
      return null;
    }

    const previous = past[past.length - 1];
    const newPast = past.slice(0, -1);

    set((current) => ({
      past: newPast,
      present: previous,
      future: current.present ? [current.present, ...current.future] : current.future,
    }));

    return previous;
  },

  // Redo to next state
  redo: () => {
    const { future, present } = get();
    
    if (future.length === 0) {
      return null;
    }

    const next = future[0];
    const newFuture = future.slice(1);

    set((current) => ({
      past: current.present ? [...current.past, current.present] : current.past,
      present: next,
      future: newFuture,
    }));

    return next;
  },

  // Check if undo is available
  canUndo: () => {
    return get().past.length > 0;
  },

  // Check if redo is available
  canRedo: () => {
    return get().future.length > 0;
  },

  // Clear all history
  clearHistory: () => {
    set({
      past: [],
      present: null,
      future: [],
    });
  },

  // Set maximum history size
  setMaxHistorySize: (size) => {
    set((current) => {
      const newPast = current.past.slice(-size);
      return {
        maxHistorySize: size,
        past: newPast,
      };
    });
  },
}));
