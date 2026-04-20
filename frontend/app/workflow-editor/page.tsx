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
      alert('Authentication required. Please sign in to save workflows.');
      return;
    }

    const validation = validateWorkflow();
    if (!validation.valid) {
      setShowValidationErrors(true);
      alert(
        `Workflow validation failed:\n\n${validation.errors.length} error(s) found\n\nPlease fix the errors before saving.`
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
      alert('Workflow is valid!');
      setShowValidationErrors(false);
    } else {
      setShowValidationErrors(true);
      const errorCount = validation.errors.length;
      const nodeErrorCount = validation.nodeErrors?.size || 0;
      alert(
        `Workflow validation failed:\n\n${errorCount} error(s) found across ${nodeErrorCount} node(s)\n\nCheck the canvas for detailed error messages.`
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
        created_by: user?.id || 'guest',
        updated_at: new Date().toISOString(),
      };
      exportWorkflow(metadata);
      alert('Workflow exported successfully!');
    } catch (error: any) {
      alert(`Failed to export workflow: ${error.message}`);
    }
  };

  const handleImportWorkflow = async (file: File) => {
    try {
      await importWorkflow(file);
      setShowImportDialog(false);
      alert('Workflow imported successfully!');
    } catch (error: any) {
      alert(`Failed to import workflow: ${error.message}`);
    }
  };

  const handleFileUploaded = (jobId: string, filename: string) => {
    console.log(`File uploaded: ${filename} (Job ID: ${jobId})`);
    setShowFileUpload(false);
  };

  return (
    <div className="workflow-editor-container">
      <header className="workflow-header bg-gradient-to-r from-slate-900 to-slate-800 border-b border-slate-700 px-6 py-4 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Auralis Workflow Editor</h1>
            <p className="text-sm text-slate-300 mt-1">Design your voice agent workflow</p>
          </div>
          
          <div className="flex gap-3">
            <a
              href="/"
              className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors font-medium shadow-md"
            >
              Home
            </a>
            <a
              href="/graph-explorer"
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-md"
            >
              Graph Explorer
            </a>
            <button
              onClick={() => {
                setShowVoiceBuilder(!showVoiceBuilder);
                if (!showVoiceBuilder) {
                  setShowTestPanel(false);
                  setShowFileUpload(false);
                }
              }}
              className={`px-4 py-2 rounded-lg transition-colors font-medium shadow-md ${
                showVoiceBuilder
                  ? 'bg-blue-700 text-white'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              Build with Voice
            </button>
            <button
              onClick={() => {
                if (!token || !user) {
                  alert('Authentication required. Please sign in to upload files.');
                  return;
                }
                setShowFileUpload(!showFileUpload);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium shadow-md"
            >
              Upload Files
            </button>
            <button
              onClick={() => {
                if (!token) {
                  alert('Authentication required. Please sign in to test workflows.');
                  return;
                }
                setShowTestPanel(!showTestPanel);
                if (!showTestPanel) {
                  setShowVoiceBuilder(false);
                }
              }}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium shadow-md"
            >
              Test Workflow
            </button>
            <button
              onClick={handleExportWorkflow}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-md"
            >
              Export
            </button>
            <button
              onClick={() => setShowImportDialog(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-md"
            >
              Import
            </button>
            <button
              onClick={handleValidateWorkflow}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors font-medium shadow-md"
            >
              Validate
            </button>
            <button
              onClick={handleSaveWorkflow}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium shadow-md"
            >
              Save
            </button>
            <button
              onClick={handleClearWorkflow}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium shadow-md"
            >
              Clear
            </button>
          </div>
        </div>
      </header>

      <div className="workflow-content">
        <aside className="workflow-sidebar bg-slate-50 border-r border-slate-200">
          <NodePalette />
        </aside>

        <main className="workflow-canvas-area bg-slate-100">
          <WorkflowCanvas
            onNodeSelect={setSelectedNode}
            onFileUpload={(_file, position) => {
              console.log('File dropped at position:', position);
            }}
            showValidationErrors={showValidationErrors}
          />
        </main>

        <aside className="workflow-config-panel bg-white border-l border-slate-200 p-6">
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

      {showFileUpload && token && user && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-800">Upload Knowledge Files</h2>
              <button
                onClick={() => setShowFileUpload(false)}
                className="text-slate-500 hover:text-slate-700 text-2xl leading-none"
              >
                &times;
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

      {showTestPanel && token && (
        <TestPanel token={token} onClose={() => setShowTestPanel(false)} />
      )}

      {showImportDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-slate-800">Import Workflow</h2>
              <button
                onClick={() => setShowImportDialog(false)}
                className="text-slate-500 hover:text-slate-700 text-2xl leading-none"
              >
                &times;
              </button>
            </div>
            <div className="p-6">
              <p className="text-sm text-slate-600 mb-4">
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
                className="block w-full text-sm text-slate-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-lg file:border-0
                  file:text-sm file:font-semibold
                  file:bg-indigo-50 file:text-indigo-700
                  hover:file:bg-indigo-100
                  cursor-pointer"
              />
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-xs text-yellow-800">
                  Warning: Importing will clear the current workflow. Make sure to export your current work first if needed.
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
        }

        .workflow-config-panel {
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
}
