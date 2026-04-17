'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import WorkflowCanvas from '@/components/WorkflowCanvas';
import NodePalette from '@/components/NodePalette';
import FileDropZone from '@/components/FileDropZone';
import ConfigurationPanel from '@/components/ConfigurationPanel';
import TestPanel from '@/components/TestPanel';
import VoiceBuilder from '@/components/VoiceBuilder';
import { useWorkflowStore, WorkflowNode } from '@/stores/workflowStore';

export default function WorkflowEditorPage() {
  const { token, user } = useAuth();
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [showValidationErrors, setShowValidationErrors] = useState(false);
  const [showTestPanel, setShowTestPanel] = useState(false);
  const [showVoiceBuilder, setShowVoiceBuilder] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  
  const { validateWorkflow, saveWorkflow, clearWorkflow, exportWorkflow, importWorkflow } = useWorkflowStore();

  const handleSaveWorkflow = async () => {
    if (!token || !user) {
      alert('Please log in to save workflows');
      return;
    }

    // Validate workflow
    const validation = validateWorkflow();
    if (!validation.valid) {
      setShowValidationErrors(true);
      alert(
        `Workflow validation failed:\n\n` +
        `${validation.errors.length} error(s) found\n\n` +
        `Please fix the errors before saving.`
      );
      return;
    }

    try {
      const metadata = {
        workflow_name: 'My Workflow',
        description: 'Workflow created in visual editor',
        created_by: user.id,
        updated_at: new Date().toISOString(),
      };

      await saveWorkflow(token, 'agent_123', metadata);
      setShowValidationErrors(false);
      alert('Workflow saved successfully!');
    } catch (error: any) {
      alert(`Failed to save workflow: ${error.message}`);
    }
  };

  const handleValidateWorkflow = () => {
    const validation = validateWorkflow();
    if (validation.valid) {
      alert('✅ Workflow is valid!');
      setShowValidationErrors(false);
    } else {
      // Show validation errors on canvas
      setShowValidationErrors(true);
      
      // Also show alert with summary
      const errorCount = validation.errors.length;
      const nodeErrorCount = validation.nodeErrors?.size || 0;
      alert(
        `❌ Workflow validation failed:\n\n` +
        `${errorCount} error(s) found across ${nodeErrorCount} node(s)\n\n` +
        `Check the canvas for detailed error messages.`
      );
    }
  };

  const handleClearWorkflow = () => {
    if (confirm('Are you sure you want to clear the entire workflow?')) {
      clearWorkflow();
    }
  };

  const handleExportWorkflow = () => {
    try {
      const metadata = {
        workflow_name: 'My Workflow',
        description: 'Exported workflow from visual editor',
        created_by: user?.id || 'unknown',
        updated_at: new Date().toISOString(),
      };
      exportWorkflow(metadata);
      alert('✅ Workflow exported successfully!');
    } catch (error: any) {
      alert(`❌ Failed to export workflow: ${error.message}`);
    }
  };

  const handleImportWorkflow = async (file: File) => {
    try {
      await importWorkflow(file);
      setShowImportDialog(false);
      alert('✅ Workflow imported successfully!');
    } catch (error: any) {
      alert(`❌ Failed to import workflow: ${error.message}`);
    }
  };

  const handleImportButtonClick = () => {
    setShowImportDialog(true);
  };

  const handleFileUploaded = (jobId: string, filename: string) => {
    console.log(`File uploaded: ${filename} (Job ID: ${jobId})`);
    setShowFileUpload(false);
  };

  return (
    <div className="workflow-editor-container">
      {/* Header */}
      <header className="workflow-header bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Workflow Editor</h1>
            <p className="text-sm text-gray-600 mt-1">Design your voice agent workflow</p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={() => {
                setShowVoiceBuilder(!showVoiceBuilder);
                if (!showVoiceBuilder) {
                  setShowTestPanel(false);
                  setShowFileUpload(false);
                }
              }}
              className={`px-4 py-2 rounded-lg transition-colors ${
                showVoiceBuilder
                  ? 'bg-blue-600 text-white'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              🎤 Build with Voice
            </button>
            <button
              onClick={() => setShowFileUpload(!showFileUpload)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              📁 Upload Files
            </button>
            <button
              onClick={() => {
                setShowTestPanel(!showTestPanel);
                if (!showTestPanel) {
                  setShowVoiceBuilder(false);
                }
              }}
              className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
            >
              🧪 Test Workflow
            </button>
            <button
              onClick={handleExportWorkflow}
              className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
            >
              📤 Export
            </button>
            <button
              onClick={handleImportButtonClick}
              className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
            >
              📥 Import
            </button>
            <button
              onClick={handleValidateWorkflow}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
            >
              ✓ Validate
            </button>
            <button
              onClick={handleSaveWorkflow}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              💾 Save
            </button>
            <button
              onClick={handleClearWorkflow}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
            >
              🗑️ Clear
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="workflow-content">
        {/* Node Palette */}
        <aside className="workflow-sidebar">
          <NodePalette />
        </aside>

        {/* Canvas */}
        <main className="workflow-canvas-area">
          <WorkflowCanvas
            onNodeSelect={setSelectedNode}
            onFileUpload={(_file, position) => {
              if (token && user) {
                // Handle file upload at specific position
                console.log('File dropped at position:', position);
              }
            }}
            showValidationErrors={showValidationErrors}
          />
        </main>

        {/* Configuration Panel or Voice Builder */}
        <aside className="workflow-config-panel bg-white border-l border-gray-200 p-6">
          {showVoiceBuilder ? (
            <VoiceBuilder
              onCommandExecuted={(action, parameters) => {
                console.log('Voice command executed:', action, parameters);
              }}
            />
          ) : (
            <ConfigurationPanel selectedNode={selectedNode} />
          )}
        </aside>
      </div>

      {/* File Upload Modal */}
      {showFileUpload && token && user && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-800">Upload Knowledge Files</h2>
              <button
                onClick={() => setShowFileUpload(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <FileDropZone
              token={token}
              companyId={user.companyId || 'default'}
              onFileUploaded={handleFileUploaded}
            />
          </div>
        </div>
      )}

      {/* Test Panel */}
      {showTestPanel && token && (
        <TestPanel token={token} onClose={() => setShowTestPanel(false)} />
      )}

      {/* Import Dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-800">Import Workflow</h2>
              <button
                onClick={() => setShowImportDialog(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <div className="p-6">
              <p className="text-sm text-gray-600 mb-4">
                Select a workflow JSON file to import. This will replace the current workflow on the canvas.
              </p>
              <input
                type="file"
                accept=".json"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    handleImportWorkflow(file);
                  }
                }}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-indigo-50 file:text-indigo-700
                  hover:file:bg-indigo-100
                  cursor-pointer"
              />
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-xs text-yellow-800">
                  ⚠️ Warning: Importing will clear the current workflow. Make sure to export your current work first if needed.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .workflow-editor-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          overflow: hidden;
        }

        .workflow-header {
          flex-shrink: 0;
        }

        .workflow-content {
          flex: 1;
          display: grid;
          grid-template-columns: 280px 1fr 320px;
          overflow: hidden;
        }

        .workflow-sidebar {
          overflow-y: auto;
        }

        .workflow-canvas-area {
          position: relative;
          background: #f9fafb;
        }

        .workflow-config-panel {
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
}
