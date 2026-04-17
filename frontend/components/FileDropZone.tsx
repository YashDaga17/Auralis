'use client';

import React, { useState, useCallback } from 'react';
import { useKnowledgeStore } from '@/stores/knowledgeStore';
import { useWorkflowStore, WorkflowNode } from '@/stores/workflowStore';

interface FileDropZoneProps {
  token: string;
  companyId: string;
  onFileUploaded?: (jobId: string, filename: string) => void;
}

const SUPPORTED_FILE_TYPES = [
  '.pdf',
  '.docx',
  '.txt',
  '.csv',
  '.json',
  '.md',
];

const SUPPORTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/csv',
  'application/json',
  'text/markdown',
];

export default function FileDropZone({ token, companyId, onFileUploaded }: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map());
  
  const { uploadFile, startPolling } = useKnowledgeStore();
  const { addNode } = useWorkflowStore();

  const validateFile = (file: File): boolean => {
    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    const isValidType = SUPPORTED_FILE_TYPES.includes(fileExtension) || 
                       SUPPORTED_MIME_TYPES.includes(file.type);
    
    if (!isValidType) {
      alert(`Unsupported file type. Supported types: ${SUPPORTED_FILE_TYPES.join(', ')}`);
      return false;
    }

    // Check file size (max 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      alert('File size exceeds 50MB limit');
      return false;
    }

    return true;
  };

  const handleFileUpload = useCallback(
    async (file: File, position?: { x: number; y: number }) => {
      if (!validateFile(file)) return;

      setIsUploading(true);
      
      try {
        // Generate collection name from filename
        const collectionName = file.name
          .replace(/\.[^/.]+$/, '') // Remove extension
          .replace(/[^a-zA-Z0-9_]/g, '_') // Replace special chars
          .toLowerCase();

        // Upload file
        const jobId = await uploadFile(token, file, collectionName, companyId);
        
        // Create Knowledge Node on canvas at drop position or default position
        const nodePosition = position || { x: 250, y: 250 };
        const knowledgeNode: WorkflowNode = {
          id: `knowledge_${Date.now()}`,
          type: 'knowledge',
          position: nodePosition,
          data: {
            label: file.name,
            config: {
              filename: file.name,
              collection_name: collectionName,
              job_id: jobId,
              chunk_count: 0,
            },
          },
        };

        addNode(knowledgeNode);

        // Start polling for upload status
        startPolling(token, jobId, (job) => {
          if (job.status === 'completed') {
            // Update node with chunk count
            const updatedNode: WorkflowNode = {
              ...knowledgeNode,
              data: {
                ...knowledgeNode.data,
                config: {
                  ...knowledgeNode.data.config,
                  chunk_count: job.chunk_count || 0,
                },
              },
            };
            
            // Note: In a real implementation, you'd update the node in the store
            console.log('Upload completed:', job);
          } else if (job.status === 'failed') {
            alert(`Upload failed: ${job.error}`);
          }
        });

        if (onFileUploaded) {
          onFileUploaded(jobId, file.name);
        }
      } catch (error: any) {
        alert(`Upload failed: ${error.message}`);
      } finally {
        setIsUploading(false);
      }
    },
    [token, companyId, uploadFile, addNode, startPolling, onFileUploaded]
  );

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        // Handle first file only for now
        handleFileUpload(files[0]);
      }
    },
    [handleFileUpload]
  );

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileUpload(files[0]);
      }
    },
    [handleFileUpload]
  );

  return (
    <div className="file-drop-zone-container p-4">
      <div
        className={`file-drop-zone border-2 border-dashed rounded-lg p-8 text-center transition-all ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        } ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <input
          type="file"
          id="file-upload"
          className="hidden"
          accept={SUPPORTED_FILE_TYPES.join(',')}
          onChange={onFileInputChange}
          disabled={isUploading}
        />
        
        <label htmlFor="file-upload" className="cursor-pointer">
          <div className="text-4xl mb-4">📁</div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">
            {isUploading ? 'Uploading...' : 'Upload Knowledge Files'}
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Drag and drop files here or click to browse
          </p>
          <p className="text-xs text-gray-500">
            Supported formats: PDF, DOCX, TXT, CSV, JSON, Markdown
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Maximum file size: 50MB
          </p>
        </label>
      </div>

      <style jsx>{`
        .file-drop-zone {
          min-height: 200px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }
      `}</style>
    </div>
  );
}
