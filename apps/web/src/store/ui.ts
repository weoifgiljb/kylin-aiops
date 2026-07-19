import { create } from 'zustand'

interface UiState {
  selectedIncidentId: string | null
  selectedNodeId: string | null
  setSelectedIncidentId: (value: string | null) => void
  setSelectedNodeId: (value: string | null) => void
}

export const useUiStore = create<UiState>((set) => ({
  selectedIncidentId: null,
  selectedNodeId: null,
  setSelectedIncidentId: (selectedIncidentId) => set({ selectedIncidentId }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
}))
