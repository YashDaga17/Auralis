import { create } from 'zustand';
import { createApiClient } from '@/lib/api-client';

export interface UploadJob {
  job_id: string;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  collection_name?: string;
  chunk_count?: number;
  created_at: string;
}

export interface QdrantCollection {
  name: string;
  vectors_count: number;
  points_count: number;
  status: string;
}

interface KnowledgeState {
  uploadJobs: Map<string, UploadJob>;
  collections: QdrantCollection[];
  isPolling: boolean;
  
  // File upload operations
  uploadFile: (token: string, file: File, collectionName: string, companyId: string) => Promise<string>;
  getUploadStatus: (token: string, jobId: string) => Promise<UploadJob>;
  startPolling: (token: string, jobId: string, onComplete?: (job: UploadJob) => void) => void;
  stopPolling: () => void;
  
  // Collection operations
  listCollections: (token: string, companyId: string) => Promise<void>;
  
  // State management
  updateJobStatus: (jobId: string, updates: Partial<UploadJob>) => void;
  clearJobs: () => void;
}

let pollingInterval: NodeJS.Timeout | null = null;

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  uploadJobs: new Map(),
  collections: [],
  isPolling: false,

  // Upload file with progress tracking
  uploadFile: async (token, file, collectionName, companyId) => {
    const apiClient = createApiClient(token);
    
    // Create FormData for file upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', collectionName);
    formData.append('company_id', companyId);

    try {
      const response = await apiClient.post('/api/knowledge/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const jobId = response.data.job_id;
      
      // Initialize job in state
      const job: UploadJob = {
        job_id: jobId,
        filename: file.name,
        status: 'pending',
        progress: 0,
        collection_name: collectionName,
        created_at: new Date().toISOString(),
      };

      set((state) => {
        const newJobs = new Map(state.uploadJobs);
        newJobs.set(jobId, job);
        return { uploadJobs: newJobs };
      });

      return jobId;
    } catch (error: any) {
      throw new Error(`Failed to upload file: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get upload status
  getUploadStatus: async (token, jobId) => {
    const apiClient = createApiClient(token);

    try {
      const response = await apiClient.get(`/api/knowledge/upload/${jobId}/status`);
      const job: UploadJob = response.data;

      // Update job in state
      set((state) => {
        const newJobs = new Map(state.uploadJobs);
        newJobs.set(jobId, job);
        return { uploadJobs: newJobs };
      });

      return job;
    } catch (error: any) {
      throw new Error(`Failed to get upload status: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Start polling for upload status
  startPolling: (token, jobId, onComplete) => {
    const { getUploadStatus, stopPolling } = get();
    
    // Clear any existing polling
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    set({ isPolling: true });

    // Poll every 2 seconds
    pollingInterval = setInterval(async () => {
      try {
        const job = await getUploadStatus(token, jobId);

        // Stop polling if job is complete or failed
        if (job.status === 'completed' || job.status === 'failed') {
          stopPolling();
          if (onComplete) {
            onComplete(job);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        stopPolling();
      }
    }, 2000);
  },

  // Stop polling
  stopPolling: () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
    set({ isPolling: false });
  },

  // List all collections
  listCollections: async (token, companyId) => {
    const apiClient = createApiClient(token);

    try {
      const response = await apiClient.get('/api/knowledge/collections', {
        params: { company_id: companyId },
      });

      set({ collections: response.data.collections });
    } catch (error: any) {
      throw new Error(`Failed to list collections: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Update job status
  updateJobStatus: (jobId, updates) => {
    set((state) => {
      const newJobs = new Map(state.uploadJobs);
      const existingJob = newJobs.get(jobId);
      
      if (existingJob) {
        newJobs.set(jobId, { ...existingJob, ...updates });
      }
      
      return { uploadJobs: newJobs };
    });
  },

  // Clear all jobs
  clearJobs: () => {
    set({ uploadJobs: new Map() });
  },
}));
