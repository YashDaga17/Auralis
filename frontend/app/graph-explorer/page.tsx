'use client';

import { useAuth } from '@/hooks/useAuth';
import GraphExplorer from '@/components/GraphExplorer';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function GraphExplorerPage() {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      <div className="graph-explorer-page">
        {/* Header */}
        <header className="graph-header bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Knowledge Graph Explorer</h1>
              <p className="text-sm text-gray-600 mt-1">
                Visualize and explore entity relationships extracted from your documents
              </p>
            </div>
            <div className="flex gap-3">
              <a
                href="/workflow-editor"
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                ← Back to Workflow Editor
              </a>
            </div>
          </div>
        </header>

        {/* Graph Explorer Component */}
        <div className="graph-explorer-content">
          {user?.companyId ? (
            <GraphExplorer companyId={user.companyId} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-600">Loading user information...</p>
            </div>
          )}
        </div>

        <style jsx>{`
          .graph-explorer-page {
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
          }

          .graph-header {
            flex-shrink: 0;
          }

          .graph-explorer-content {
            flex: 1;
            overflow: hidden;
          }
        `}</style>
      </div>
    </ProtectedRoute>
  );
}
