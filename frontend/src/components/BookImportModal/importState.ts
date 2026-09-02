export interface ImportDialogState {
  fileName?: string;
  sessionId?: string;
  error?: string;
  title: string;
  authors: string;
  uploadProgress: number;
}

export const initialImportDialogState: ImportDialogState = {
  title: '',
  authors: '',
  uploadProgress: 0,
};

export type ImportDialogAction =
  | { type: 'patch'; value: Partial<ImportDialogState> }
  | { type: 'reset' };

export const importDialogReducer = (
  state: ImportDialogState,
  action: ImportDialogAction
): ImportDialogState => action.type === 'reset'
  ? initialImportDialogState
  : { ...state, ...action.value };
