# Store Architecture

## Overview

The Visual Workflow Engine uses three independent Zustand stores that work together to manage the application state.

## Store Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     React Components                         │
│  (WorkflowCanvas, ConfigPanel, FileUploader, Toolbar)       │
└────────────┬────────────────┬────────────────┬──────────────┘
             │                │                │
             ▼                ▼                ▼
    ┌────────────────┐ ┌──────────────┐ ┌─────────────┐
    │ Workflow Store │ │Knowledge Store│ │History Store│
    │                │ │               │ │             │
    │ • nodes        │ │ • uploadJobs  │ │ • past      │
    │ • edges        │ │ • collections │ │ • present   │
    │ • selectedNode │ │ • isPolling   │ │ • future    │
    └────────┬───────┘ └───────┬───────┘ └──────┬──────┘
             │                 │                 │
             │                 │                 │
             ▼                 ▼                 ▼
    ┌────────────────┐ ┌──────────────┐ ┌─────────────┐
    │  API Client    │ │  API Client  │ │   Memory    │
    │                │ │              │ │             │
    │ • POST /api/   │ │ • POST /api/ │ │ • State     │
    │   workflows    │ │   knowledge/ │ │   snapshots │
    │ • GET /api/    │ │   upload     │ │             │
    │   workflows/   │ │ • GET /api/  │ │             │
    │   {id}         │ │   knowledge/ │ │             │
    │                │ │   collections│ │             │
    └────────────────┘ └──────────────┘ └─────────────┘
```

## Data Flow

### 1. Workflow Creation Flow

```
User Action (Add Node)
    ↓
workflowStore.addNode()
    ↓
Update nodes array
    ↓
Trigger React re-render
    ↓
historyStore.recordState()
    ↓
Save state snapshot
```

### 2. File Upload Flow

```
User Action (Drop File)
    ↓
knowledgeStore.uploadFile()
    ↓
POST /api/knowledge/upload
    ↓
Receive job_id
    ↓
knowledgeStore.startPolling()
    ↓
Poll GET /api/knowledge/upload/{job_id}/status
    ↓
Update uploadJobs map
    ↓
On completion callback
    ↓
workflowStore.addNode() (create knowledge node)
    ↓
historyStore.recordState()
```

### 3. Undo/Redo Flow

```
User Action (Undo)
    ↓
historyStore.undo()
    ↓
Get previous state from past[]
    ↓
Move present to future[]
    ↓
Return previous state
    ↓
Component applies state to workflowStore
    ↓
workflowStore.setState({ nodes, edges })
    ↓
Trigger React re-render
```

### 4. Save Workflow Flow

```
User Action (Save)
    ↓
workflowStore.validateWorkflow()
    ↓
Check: single trigger, no cycles, required fields
    ↓
workflowStore.compileWorkflow()
    ↓
Generate WorkflowJSON
    ↓
workflowStore.saveWorkflow()
    ↓
POST /api/workflows
    ↓
Success/Error response
```

## State Management Patterns

### 1. Immutable Updates

All stores use immutable state updates:

```typescript
// ❌ Bad - Mutates state
addNode: (node) => {
  state.nodes.push(node);
}

// ✅ Good - Creates new array
addNode: (node) => {
  set((state) => ({
    nodes: [...state.nodes, node]
  }));
}
```

### 2. Derived State

Use selectors for computed values:

```typescript
// In component
const nodeCount = useWorkflowStore((state) => state.nodes.length);
const hasUnsavedChanges = useWorkflowStore((state) => 
  state.nodes.length > 0 && !state.lastSavedAt
);
```

### 3. Action Composition

Stores can call other stores:

```typescript
// In component - compose actions
const handleFileUploadComplete = (job: UploadJob) => {
  // Create knowledge node
  workflowStore.addNode({
    id: `knowledge-${job.job_id}`,
    type: 'knowledge',
    data: { label: job.filename, config: { ... } }
  });
  
  // Record state for undo
  historyStore.recordState({
    nodes: workflowStore.getState().nodes,
    edges: workflowStore.getState().edges
  });
};
```

## Store Responsibilities

### Workflow Store
- **Primary**: Canvas state (nodes, edges)
- **Secondary**: Validation, compilation, persistence
- **Does NOT**: Handle undo/redo, file uploads

### Knowledge Store
- **Primary**: File upload management
- **Secondary**: Collection listing, job tracking
- **Does NOT**: Create workflow nodes (component responsibility)

### History Store
- **Primary**: Undo/redo state management
- **Secondary**: History size limiting
- **Does NOT**: Apply states to workflow store (component responsibility)

## Performance Optimization

### 1. Selective Subscriptions

```typescript
// ❌ Bad - Re-renders on any state change
const store = useWorkflowStore();

// ✅ Good - Only re-renders when nodes change
const nodes = useWorkflowStore((state) => state.nodes);
```

### 2. Memoized Selectors

```typescript
// Create memoized selector
const selectNodeById = (nodeId: string) => (state: WorkflowState) =>
  state.nodes.find(n => n.id === nodeId);

// Use in component
const node = useWorkflowStore(selectNodeById('node-1'));
```

### 3. Batch Updates

```typescript
// ❌ Bad - Multiple re-renders
addNode(node1);
addNode(node2);
addNode(node3);

// ✅ Good - Single re-render
set((state) => ({
  nodes: [...state.nodes, node1, node2, node3]
}));
```

## Error Handling Strategy

### 1. Async Operations

All async operations throw errors:

```typescript
try {
  await saveWorkflow(token, agentId, metadata);
  toast.success('Workflow saved');
} catch (error) {
  toast.error(error.message);
  console.error('Save failed:', error);
}
```

### 2. Validation Errors

Validation returns structured errors:

```typescript
const validation = validateWorkflow();
if (!validation.valid) {
  validation.errors.forEach(error => {
    toast.error(error);
  });
  return;
}
```

### 3. Network Errors

API client errors include response details:

```typescript
catch (error: any) {
  const message = error.response?.data?.detail || error.message;
  throw new Error(`Failed to save: ${message}`);
}
```

## Testing Strategy

### Unit Tests

Test store logic in isolation:

```typescript
describe('WorkflowStore', () => {
  beforeEach(() => {
    useWorkflowStore.setState({ nodes: [], edges: [] });
  });

  it('should add node', () => {
    const { addNode } = useWorkflowStore.getState();
    addNode(mockNode);
    expect(useWorkflowStore.getState().nodes).toHaveLength(1);
  });
});
```

### Integration Tests

Test store interactions:

```typescript
it('should create knowledge node after upload', async () => {
  const jobId = await uploadFile(token, file, collection, companyId);
  startPolling(token, jobId, (job) => {
    addNode(createKnowledgeNode(job));
  });
  
  await waitFor(() => {
    expect(useWorkflowStore.getState().nodes).toHaveLength(1);
  });
});
```

## Best Practices

1. **Keep stores focused**: Each store has a single responsibility
2. **Use TypeScript**: All stores are fully typed
3. **Immutable updates**: Never mutate state directly
4. **Error handling**: Always handle async errors
5. **Selective subscriptions**: Only subscribe to needed state
6. **Composition over inheritance**: Compose actions in components
7. **Test coverage**: Unit test all store logic
8. **Documentation**: Document complex logic and edge cases

## Migration Path

If you need to add middleware later:

```typescript
import { devtools, persist } from 'zustand/middleware';

export const useWorkflowStore = create<WorkflowState>()(
  devtools(
    persist(
      (set, get) => ({
        // ... store implementation
      }),
      { name: 'workflow-store' }
    )
  )
);
```

## References

- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Flow Documentation](https://reactflow.dev/)
- [Design Document](../../.kiro/specs/visual-workflow-engine/design.md)
- [Requirements Document](../../.kiro/specs/visual-workflow-engine/requirements.md)
