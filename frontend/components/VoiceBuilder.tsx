'use client';

/**
 * VoiceBuilder Component
 * 
 * Provides voice-based workflow building using Vapi integration.
 * Users can create and modify workflows through natural language voice commands.
 * 
 * Requirements: 21.1, 21.2, 21.8
 */

import { useState, useEffect, useRef } from 'react';
import Vapi from '@vapi-ai/web';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { apiClient } from '@/lib/api-client';

interface ConversationTurn {
  user: string;
  assistant: string;
  timestamp: Date;
}

interface VoiceBuilderProps {
  onCommandExecuted?: (action: string, parameters: any) => void;
}

export default function VoiceBuilder({ onCommandExecuted }: VoiceBuilderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<ConversationTurn[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [textInputMode, setTextInputMode] = useState(true); // Default to text mode
  const [textInput, setTextInput] = useState('');
  
  const vapiRef = useRef<Vapi | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  
  const { nodes, edges, addNode, addEdge, updateNode, deleteNode, saveWorkflow } = useWorkflowStore();

  useEffect(() => {
    // Skip Vapi initialization if starting in text mode
    if (textInputMode) {
      return;
    }

    // Initialize Vapi client
    const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
    
    if (!publicKey) {
      setError('Vapi public key not configured. Using text mode instead.');
      setTextInputMode(true);
      return;
    }

    try {
      vapiRef.current = new Vapi(publicKey);
      
      // Set up event listeners
      vapiRef.current.on('call-start', () => {
        console.log('Voice call started');
        setIsConnected(true);
        setIsListening(true);
        setError(null);
      });

      vapiRef.current.on('call-end', () => {
        console.log('Voice call ended');
        setIsConnected(false);
        setIsListening(false);
      });

      vapiRef.current.on('speech-start', () => {
        console.log('User started speaking');
        setIsListening(true);
      });

      vapiRef.current.on('speech-end', () => {
        console.log('User stopped speaking');
        setIsListening(false);
      });

      vapiRef.current.on('message', (message: any) => {
        console.log('Message received:', message);
        
        // Handle transcript updates
        if (message.type === 'transcript' && message.transcriptType === 'final') {
          const userMessage = message.transcript;
          setCurrentTranscript(userMessage);
        }
        
        // Handle assistant responses
        if (message.type === 'function-call') {
          handleFunctionCall(message);
        }
      });

      vapiRef.current.on('error', (error: any) => {
        console.error('Vapi error:', error);
        
        // Handle specific error types
        let errorMessage = 'Voice connection error';
        
        if (error.error?.message?.msg === 'Meeting has ended') {
          errorMessage = 'Voice session ended. This may be due to assistant configuration. Please check your Vapi assistant settings.';
        } else if (error.message) {
          errorMessage = error.message;
        } else if (error.error?.errorMsg) {
          errorMessage = error.error.errorMsg;
        }
        
        setError(errorMessage);
        setIsConnected(false);
        setIsListening(false);
      });

    } catch (err) {
      console.error('Failed to initialize Vapi:', err);
      setError('Failed to initialize voice system');
    }

    return () => {
      if (vapiRef.current) {
        vapiRef.current.stop();
      }
    };
  }, []);

  useEffect(() => {
    // Auto-scroll transcript to bottom
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const handleFunctionCall = async (message: any) => {
    // This would be called when Vapi triggers a function
    // For now, we'll parse commands through our backend
    if (currentTranscript) {
      await parseAndExecuteCommand(currentTranscript);
    }
  };

  const parseAndExecuteCommand = async (userCommand: string) => {
    try {
      // Call backend to parse the voice command
      const response = await apiClient.post('/api/voice-builder/parse-command', {
        transcript: userCommand,
        workflow_context: {
          nodes,
          edges
        },
        conversation_history: transcript.slice(-3).map(t => ({
          user: t.user,
          assistant: t.assistant
        }))
      });

      const { action, parameters, confirmation_message, requires_clarification, clarification_question } = response.data;

      // Add to transcript
      const newTurn: ConversationTurn = {
        user: userCommand,
        assistant: requires_clarification ? clarification_question : confirmation_message,
        timestamp: new Date()
      };
      setTranscript(prev => [...prev, newTurn]);
      setCurrentTranscript('');

      // Execute the action if no clarification needed
      if (!requires_clarification) {
        await executeWorkflowAction(action, parameters);
        
        // Notify parent component
        if (onCommandExecuted) {
          onCommandExecuted(action, parameters);
        }
      }

      // Speak the confirmation/clarification
      if (vapiRef.current && isConnected) {
        vapiRef.current.send({
          type: 'add-message',
          message: {
            role: 'assistant',
            content: requires_clarification ? clarification_question : confirmation_message
          }
        });
      }

    } catch (err: any) {
      console.error('Failed to parse command:', err);
      const errorMessage = 'Sorry, I had trouble understanding that command. Could you try rephrasing?';
      setTranscript(prev => [...prev, {
        user: userCommand,
        assistant: errorMessage,
        timestamp: new Date()
      }]);
      setError(err.message);
    }
  };

  const executeWorkflowAction = async (action: string, parameters: any) => {
    try {
      switch (action) {
        case 'add_node':
          const nodeId = `${parameters.node_type}_${Date.now()}`;
          const newNode = {
            id: nodeId,
            type: parameters.node_type,
            position: parameters.position || { 
              x: Math.random() * 400 + 100, 
              y: Math.random() * 300 + 100 
            },
            data: {
              label: parameters.label || `${parameters.node_type} Node`,
              config: parameters.config || {}
            }
          };
          addNode(newNode);
          break;

        case 'connect_nodes':
          const edgeId = `edge_${Date.now()}`;
          const newEdge = {
            id: edgeId,
            source: parameters.source_node_id,
            target: parameters.target_node_id,
            label: parameters.label
          };
          addEdge(newEdge);
          break;

        case 'configure_node':
          const nodeToUpdate = nodes.find(n => n.id === parameters.node_id);
          if (nodeToUpdate) {
            updateNode(parameters.node_id, {
              ...nodeToUpdate,
              data: {
                ...nodeToUpdate.data,
                config: {
                  ...nodeToUpdate.data.config,
                  ...parameters.config
                }
              }
            });
          }
          break;

        case 'delete_node':
          deleteNode(parameters.node_id);
          break;

        case 'save_workflow':
          await saveWorkflow(
            parameters.workflow_name || 'Voice Created Workflow',
            parameters.description || 'Created via voice commands'
          );
          break;

        default:
          console.warn('Unknown action:', action);
      }
    } catch (err) {
      console.error('Failed to execute action:', err);
      throw err;
    }
  };

  const startVoiceSession = async () => {
    if (!vapiRef.current) {
      setError('Voice system not initialized');
      return;
    }

    const assistantId = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;
    
    if (!assistantId) {
      setError('Vapi assistant ID not configured. Please set NEXT_PUBLIC_VAPI_ASSISTANT_ID in .env.local');
      return;
    }

    try {
      // Start Vapi call with workflow builder assistant
      // Use assistant configuration instead of just ID for better control
      await vapiRef.current.start({
        assistantId: assistantId,
        // Optional: Add assistant overrides for workflow building
        assistantOverrides: {
          firstMessage: "Hi! I'm ready to help you build your workflow. You can tell me to add nodes, connect them, or configure settings. What would you like to do?",
          transcriber: {
            provider: "deepgram",
            model: "nova-2",
            language: "en"
          }
        }
      });
      setError(null);
    } catch (err: any) {
      console.error('Failed to start voice session:', err);
      setError(err.message || 'Failed to start voice session. Please check your Vapi configuration.');
    }
  };

  const stopVoiceSession = () => {
    if (vapiRef.current) {
      vapiRef.current.stop();
    }
  };

  const toggleMute = () => {
    if (vapiRef.current) {
      vapiRef.current.setMuted(!isMuted);
      setIsMuted(!isMuted);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Voice Builder</h2>
          <p className="text-sm text-gray-500">Build workflows with voice commands</p>
        </div>
        
        <div className="flex items-center gap-2">
          {!textInputMode && isConnected && (
            <button
              onClick={toggleMute}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <VolumeX className="w-5 h-5 text-gray-600" />
              ) : (
                <Volume2 className="w-5 h-5 text-gray-600" />
              )}
            </button>
          )}
          
          <button
            onClick={() => {
              const newMode = !textInputMode;
              setTextInputMode(newMode);
              
              if (newMode && isConnected) {
                // Switching to text mode - stop voice
                stopVoiceSession();
              } else if (!newMode && !vapiRef.current) {
                // Switching to voice mode - initialize Vapi if needed
                const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
                if (publicKey) {
                  try {
                    vapiRef.current = new Vapi(publicKey);
                    setError(null);
                  } catch (err) {
                    console.error('Failed to initialize Vapi:', err);
                    setError('Voice mode unavailable. Please use text mode.');
                    setTextInputMode(true);
                  }
                } else {
                  setError('Voice mode not configured. Please use text mode.');
                  setTextInputMode(true);
                }
              }
            }}
            className="px-3 py-2 text-sm rounded-lg hover:bg-gray-100 transition-colors text-gray-700"
            title={textInputMode ? 'Switch to Voice Mode' : 'Switch to Text Mode'}
          >
            {textInputMode ? '🎤 Voice' : '⌨️ Text'}
          </button>
          
          {!textInputMode && (
            <button
              onClick={isConnected ? stopVoiceSession : startVoiceSession}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                isConnected
                  ? 'bg-red-500 hover:bg-red-600 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {isConnected ? (
                <>
                  <MicOff className="w-5 h-5" />
                  Stop
                </>
              ) : (
                <>
                  <Mic className="w-5 h-5" />
                  Start Voice
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Status */}
      {isConnected && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-100">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isListening ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
            <span className="text-sm text-blue-900">
              {isListening ? 'Listening...' : 'Connected - Ready for commands'}
            </span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-100">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {transcript.length === 0 && textInputMode && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-lg font-medium mb-2">Build with Commands</p>
            <p className="text-sm">Type your commands in the input box below</p>
            <p className="text-sm mt-1 text-blue-600">💡 Click "🎤 Voice" to use voice commands instead</p>
            <div className="mt-6 text-left max-w-md mx-auto space-y-2">
              <p className="text-sm font-medium text-gray-700">Example commands:</p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• "Add a RAG node that searches the customer database"</li>
                <li>• "Connect the trigger to the RAG node"</li>
                <li>• "Add an LLM node to generate a response"</li>
                <li>• "Save the workflow"</li>
              </ul>
            </div>
          </div>
        )}

        {transcript.length === 0 && !isConnected && !textInputMode && (
          <div className="text-center text-gray-500 py-8">
            <Mic className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium mb-2">Build with Voice</p>
            <p className="text-sm">Click "Start Voice" to begin creating your workflow</p>
            <p className="text-sm mt-2">Or click "⌨️ Text" to type commands instead</p>
            <div className="mt-6 text-left max-w-md mx-auto space-y-2">
              <p className="text-sm font-medium text-gray-700">Try saying:</p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• "Add a RAG node that searches the customer database"</li>
                <li>• "Connect the trigger to the RAG node"</li>
                <li>• "Add an LLM node to generate a response"</li>
                <li>• "Save the workflow"</li>
              </ul>
            </div>
          </div>
        )}

        {transcript.map((turn, index) => (
          <div key={index} className="space-y-2">
            {/* User message */}
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-blue-500 text-white rounded-lg px-4 py-2">
                <p className="text-sm">{turn.user}</p>
                <p className="text-xs opacity-75 mt-1">
                  {turn.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>

            {/* Assistant message */}
            <div className="flex justify-start">
              <div className="max-w-[80%] bg-gray-100 text-gray-900 rounded-lg px-4 py-2">
                <p className="text-sm">{turn.assistant}</p>
              </div>
            </div>
          </div>
        ))}

        {/* Current transcript (while speaking) */}
        {currentTranscript && (
          <div className="flex justify-end">
            <div className="max-w-[80%] bg-blue-400 text-white rounded-lg px-4 py-2 opacity-75">
              <p className="text-sm">{currentTranscript}</p>
              <p className="text-xs mt-1">Speaking...</p>
            </div>
          </div>
        )}

        <div ref={transcriptEndRef} />
      </div>

      {/* Help Text */}
      {isConnected && !textInputMode && (
        <div className="px-4 py-3 bg-gray-50 border-t text-xs text-gray-600">
          <p className="font-medium mb-1">Voice Commands:</p>
          <p>Add nodes, connect nodes, configure settings, delete nodes, or save your workflow</p>
        </div>
      )}

      {/* Text Input Mode (Fallback) */}
      {textInputMode && (
        <div className="px-4 py-3 bg-gray-50 border-t">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (textInput.trim()) {
                parseAndExecuteCommand(textInput);
                setTextInput('');
              }
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your command here..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Send
            </button>
          </form>
          <p className="text-xs text-gray-500 mt-2">
            Text mode - Type commands instead of speaking
          </p>
        </div>
      )}
    </div>
  );
}
