# Workflow Canvas Components

This directory contains the React Flow-based workflow canvas components for the Visual Workflow Engine.

## Components

### WorkflowCanvas
The main canvas component that provides:
- Drag-and-drop node placement from palette
- Edge creation with DAG validation (prevents cycles)
- Pan, zoom, and selection controls
- File drop zone for knowledge uploads
- Keyboard shortcuts (Delete/Backspace to remove nodes/edges)

**Props:**
- `onNodeSelect?: (node: WorkflowNode | null) => void` - Callback when a node is selected
- `onFileUpload?: (file: File, position: { x: number; y: number }) => void` - Callback when a file is dropped

### NodePalette
A sidebar component displaying all available node types:
- Trigger Node (entry point)
- RAG Node (vector search)
- LLM Node (text generation)
- Tool Node (API calls)
- Action Node (business workflows)
- Decision Node (intent routing)
- Graph Query Node (Neo4j queries)
- Multi-Source RAG Node (multiple collections)

Nodes can be dragged from the palette onto the canvas.

### FileDropZone
A file upload component that:
- Accepts PDF, DOCX, TXT, CSV, JSON, Markdown files
- Validates file types and size (max 50MB)
- Uploads files to backend API
- Creates Knowledge Nodes on canvas after upload
- Polls for upload status

**Props:**
- `token: string` - JWT authentication token
- `companyId: string` - Company ID for multi-tenant isolation
- `onFileUploaded?: (jobId: string, filename: string) => void` - Callback when upload completes

## Usage

```tsx
import WorkflowCanvas from '@/components/WorkflowCanvas';
import NodePalette from '@/components/NodePalette';
import FileDropZone from '@/components/FileDropZone';

function WorkflowEditor() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 320px', height: '100vh' }}>
      <NodePalette />
      <WorkflowCanvas 
        onNodeSelect={(node) => console.log('Selected:', node)}
      />
      <div>Configuration Panel</div>
    </div>
  );
}
```

## Features Implemented

### Task 25.1: WorkflowCanvas with React Flow
✅ Pan, zoom, and selection controls
✅ Node drag-and-drop from palette
✅ Edge creation on node connection
✅ DAG constraint enforcement (cycle detection)
✅ Keyboard shortcuts for deletion

### Task 25.3: Node Palette
✅ Display all 8 node types
✅ Drag-and-drop to canvas
✅ Visual icons and descriptions

### Task 25.4: File Drop Zone
✅ Accept PDF, DOCX, TXT, CSV, JSON, Markdown
✅ Upload to backend API
✅ Create Knowledge Node after upload
✅ File validation and progress tracking

## State Management

The components integrate with Zustand stores:
- `workflowStore` - Manages nodes, edges, and workflow operations
- `knowledgeStore` - Manages file uploads and collections

## Validation

The canvas enforces the following constraints:
- **Single Trigger Node**: Only one trigger node allowed per workflow
- **DAG Structure**: No cycles allowed in edge connections
- **Required Fields**: All nodes must have valid configuration

Use `validateWorkflow()` from the workflow store to check these constraints before saving.

### ConfigurationPanel
A dynamic configuration panel that displays node-specific forms:
- Automatically renders appropriate form based on selected node type
- Supports context variable syntax `{{variable}}`
- Provides autocomplete for available context variables
- Validates required fields before saving

**Props:**
- `selectedNode: WorkflowNode | null` - The currently selected node to configure

### TestPanel
A workflow testing interface that allows users to test workflows without saving:
- Input field for test transcript
- Execute workflow with sample input
- Timeline view showing execution logs for each node
- Display node inputs, outputs, and execution times
- Highlight failed nodes (red) and slow nodes (yellow, >200ms)
- Expandable node details with full input/output data
- Visual indicators for nodes exceeding 800ms latency target

**Props:**
- `token: string` - JWT authentication token
- `onClose?: () => void` - Callback when panel is closed

**Features:**
- Real-time execution monitoring
- Node-by-node performance tracking
- Error highlighting and debugging
- Latency warnings for optimization

## Next Steps

To complete the workflow editor:
1. ✅ Implement node configuration panel (Task 26)
2. ✅ Add workflow validation UI (Task 27)
3. ✅ Create workflow testing interface (Task 28)
4. Add import/export functionality (Task 29)
