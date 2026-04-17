# Zustand State Management Stores

This directory contains three Zustand stores for managing the Visual Workflow Engine state:

## 1. Workflow Store (`workflowStore.ts`)

Manages the workflow canvas state including nodes, edges, and workflow operations.

### Features
- **Node Management**: Add, update, delete, and select nodes
- **Edge Management**: Add and delete edges between nodes
- **Workflow Validation**: Validates single trigger node, no cycles, and required fields
- **Workflow Compilation**: Compiles visual graph to Workflow JSON format
- **Backend Integration**: Save and load workflows from the API

### Usage Example

```typescript
import { useWorkflowStore } from '@/stores';

function WorkflowCanvas() {
  const { 
    nodes, 
    edges, 
    addNode, 
    updateNode, 
    deleteNode,
    addEdge,
    validateWorkflow,
    saveWorkflow 
  } = useWorkflowStore();

  const handleAddNode = () => {
    const newNode = {
      id: `node-${Date.now()}`,
      type: 'rag',
      position: { x: 100, y: 100 },
      data: {
        label: 'RAG Node',
        config: {
          collection_name: 'my-collection',
          query_template: '{{trigger_output}}',
          result_limit: 5
        }
      }
    };
    addNode(newNode);
  };

  const handleSave = async () => {
    const validation = validateWorkflow();
    if (!validation.valid) {
      console.error('Validation errors:', validation.errors);
      return;
    }

    try {
      await saveWorkflow(token, agentId, {
        workflow_name: 'My Workflow',
        description: 'A sample workflow',
        created_by: userId,
        updated_at: new Date().toISOString()
      });
      console.log('Workflow saved successfully');
    } catch (error) {
      console.error('Save failed:', error);
    }
  };

  return (
    <div>
      <button onClick={handleAddNode}>Add Node</button>
      <button onClick={handleSave}>Save Workflow</button>
      {/* React Flow canvas */}
    </div>
  );
}
```

## 2. Knowledge Store (`knowledgeStore.ts`)

Manages file uploads, job tracking, and Qdrant collection management.

### Features
- **File Upload**: Upload files with progress tracking
- **Job Polling**: Poll for upload job status with automatic updates
- **Collection Management**: List and manage Qdrant collections
- **State Tracking**: Track multiple upload jobs simultaneously

### Usage Example

```typescript
import { useKnowledgeStore } from '@/stores';

function FileUploader() {
  const { 
    uploadFile, 
    startPolling, 
    uploadJobs,
    listCollections,
    collections 
  } = useKnowledgeStore();

  const handleFileUpload = async (file: File) => {
    try {
      const jobId = await uploadFile(
        token, 
        file, 
        'my-collection', 
        companyId
      );

      // Start polling for status
      startPolling(token, jobId, (job) => {
        if (job.status === 'completed') {
          console.log('Upload completed:', job.chunk_count, 'chunks');
        } else if (job.status === 'failed') {
          console.error('Upload failed:', job.error);
        }
      });
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const loadCollections = async () => {
    await listCollections(token, companyId);
    console.log('Collections:', collections);
  };

  return (
    <div>
      <input 
        type="file" 
        onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])} 
      />
      <button onClick={loadCollections}>Load Collections</button>
      
      {/* Display upload jobs */}
      {Array.from(uploadJobs.values()).map((job) => (
        <div key={job.job_id}>
          {job.filename}: {job.status} ({job.progress}%)
        </div>
      ))}
    </div>
  );
}
```

## 3. History Store (`historyStore.ts`)

Manages undo/redo functionality for workflow state changes.

### Features
- **State Recording**: Record workflow states for undo/redo
- **Undo/Redo**: Navigate through workflow history
- **History Limits**: Configurable maximum history size (default: 50)
- **State Validation**: Check if undo/redo is available

### Usage Example

```typescript
import { useWorkflowStore } from '@/stores/workflowStore';
import { useHistoryStore } from '@/stores/historyStore';
import { useEffect } from 'react';

function WorkflowEditor() {
  const { nodes, edges, addNode, updateNode } = useWorkflowStore();
  const { recordState, undo, redo, canUndo, canRedo } = useHistoryStore();

  // Record state changes
  useEffect(() => {
    recordState({ nodes, edges });
  }, [nodes, edges, recordState]);

  const handleUndo = () => {
    const previousState = undo();
    if (previousState) {
      // Apply previous state to workflow store
      useWorkflowStore.setState({
        nodes: previousState.nodes,
        edges: previousState.edges
      });
    }
  };

  const handleRedo = () => {
    const nextState = redo();
    if (nextState) {
      // Apply next state to workflow store
      useWorkflowStore.setState({
        nodes: nextState.nodes,
        edges: nextState.edges
      });
    }
  };

  return (
    <div>
      <button onClick={handleUndo} disabled={!canUndo()}>
        Undo
      </button>
      <button onClick={handleRedo} disabled={!canRedo()}>
        Redo
      </button>
      {/* Workflow canvas */}
    </div>
  );
}
```

## Integration Example

Here's how to use all three stores together:

```typescript
import { useWorkflowStore, useKnowledgeStore, useHistoryStore } from '@/stores';
import { useAuth } from '@/hooks/useAuth';

function WorkflowBuilder() {
  const { token, user } = useAuth();
  
  // Workflow store
  const { 
    nodes, 
    edges, 
    addNode, 
    saveWorkflow,
    validateWorkflow 
  } = useWorkflowStore();
  
  // Knowledge store
  const { 
    uploadFile, 
    startPolling,
    collections,
    listCollections 
  } = useKnowledgeStore();
  
  // History store
  const { 
    recordState, 
    undo, 
    redo, 
    canUndo, 
    canRedo 
  } = useHistoryStore();

  // Record state changes for undo/redo
  useEffect(() => {
    recordState({ nodes, edges });
  }, [nodes, edges]);

  // Load collections on mount
  useEffect(() => {
    if (token && user?.company_id) {
      listCollections(token, user.company_id);
    }
  }, [token, user]);

  const handleFileUpload = async (file: File) => {
    const jobId = await uploadFile(token, file, 'docs', user.company_id);
    
    startPolling(token, jobId, (job) => {
      if (job.status === 'completed') {
        // Create knowledge node on canvas
        addNode({
          id: `knowledge-${Date.now()}`,
          type: 'knowledge',
          position: { x: 200, y: 200 },
          data: {
            label: job.filename,
            config: {
              collection_name: job.collection_name,
              chunk_count: job.chunk_count
            }
          }
        });
      }
    });
  };

  const handleSave = async () => {
    const validation = validateWorkflow();
    if (!validation.valid) {
      alert(`Validation failed: ${validation.errors.join(', ')}`);
      return;
    }

    await saveWorkflow(token, agentId, {
      workflow_name: 'My Agent',
      description: 'Customer support agent',
      created_by: user.id,
      updated_at: new Date().toISOString()
    });
  };

  return (
    <div>
      <div className="toolbar">
        <button onClick={() => undo()} disabled={!canUndo()}>Undo</button>
        <button onClick={() => redo()} disabled={!canRedo()}>Redo</button>
        <button onClick={handleSave}>Save</button>
      </div>
      
      <input 
        type="file" 
        onChange={(e) => e.target.files && handleFileUpload(e.target.files[0])} 
      />
      
      {/* React Flow Canvas */}
    </div>
  );
}
```

## Store Architecture

### State Management Pattern

All stores follow Zustand's recommended patterns:
- **Immutable Updates**: State updates create new objects/arrays
- **Selector Pattern**: Components can subscribe to specific state slices
- **Middleware Support**: Can add devtools, persist, or immer middleware

### Error Handling

All async operations throw errors that should be caught by the consuming components:

```typescript
try {
  await saveWorkflow(token, agentId, metadata);
} catch (error) {
  console.error('Save failed:', error.message);
  // Show error to user
}
```

### Type Safety

All stores are fully typed with TypeScript interfaces exported for use in components.

## Requirements Mapping

- **Task 24.1**: `workflowStore.ts` - Workflow state management with CRUD operations
- **Task 24.3**: `knowledgeStore.ts` - File upload and collection management
- **Task 24.4**: `historyStore.ts` - Undo/redo functionality

### Requirements Coverage

- **Requirement 1.8**: Visual workflow canvas state management ✓
- **Requirement 3.1**: Workflow compilation and storage ✓
- **Requirement 22.3**: File upload with job tracking ✓
- **Requirement 24.4**: Collection listing ✓
- **Requirement 24.5**: Upload status polling ✓
- **Requirement 24.7**: Bulk upload support (via multiple uploadFile calls) ✓
