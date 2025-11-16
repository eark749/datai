import apiClient from './config';

export interface CreateChatRequest {
  title?: string;
  db_connection_id?: string;
}

export interface ChatMessageResponse {
  id: string;
  chat_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sql_query?: string;
  query_results?: any;
  dashboard_html?: string;
}

export interface ChatResponse {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  db_connection_id?: string;
  is_archived: boolean;
  messages?: ChatMessageResponse[];
}

export interface SendQueryRequest {
  message: string;
  chat_id: string;
  db_connection_id?: string;
}

export interface SendQueryResponse {
  chat_id: string;
  message_id: string;
  user_message: string;
  assistant_message: string;
  mode: string;
  sql_query?: string;
  data?: any[];
  dashboard_html?: string;
  execution_time_ms?: number;
  row_count?: number;
}

export interface ConnectDbRequest {
  db_connection_id: string;
}

/**
 * Create a new chat
 */
export const createChat = async (data?: CreateChatRequest): Promise<ChatResponse> => {
  console.log('Creating new chat:', data);
  const response = await apiClient.post<ChatResponse>('/api/new', data || {});
  console.log('Chat created:', response.data);
  return response.data;
};

/**
 * Send a query message
 */
export const sendQuery = async (data: SendQueryRequest): Promise<SendQueryResponse> => {
  console.log('Sending query:', { chatId: data.chat_id, message: data.message.substring(0, 50) });
  const response = await apiClient.post<SendQueryResponse>('/api/query', data);
  console.log('Query response received');
  return response.data;
};

/**
 * List all chats
 */
export const listChats = async (skip = 0, limit = 50): Promise<ChatResponse[]> => {
  console.log('Fetching chats');
  const response = await apiClient.get<ChatResponse[]>('/api/chats', {
    params: { skip, limit },
  });
  console.log('Chats fetched:', response.data.length);
  return response.data;
};

/**
 * Get a specific chat with all messages
 */
export const getChat = async (chatId: string): Promise<ChatResponse> => {
  console.log('Fetching chat:', chatId);
  const response = await apiClient.get<ChatResponse>(`/api/chats/${chatId}`);
  console.log('Chat fetched with', response.data.messages?.length || 0, 'messages');
  return response.data;
};

/**
 * Connect a database to a chat
 */
export const connectDatabase = async (
  chatId: string,
  dbConnectionId: string
): Promise<ChatResponse> => {
  console.log('Connecting database to chat:', chatId, dbConnectionId);
  const response = await apiClient.patch<ChatResponse>(`/api/${chatId}/connect-db`, {
    db_connection_id: dbConnectionId,
  });
  return response.data;
};

/**
 * Delete a chat
 */
export const deleteChat = async (chatId: string): Promise<void> => {
  console.log('Deleting chat:', chatId);
  await apiClient.delete(`/api/chats/${chatId}`);
  console.log('Chat deleted');
};

/**
 * Archive/Unarchive a chat
 */
export const archiveChat = async (chatId: string): Promise<ChatResponse> => {
  console.log('Archiving chat:', chatId);
  const response = await apiClient.patch<ChatResponse>(`/api/chats/${chatId}/archive`);
  console.log('Chat archive status updated');
  return response.data;
};

