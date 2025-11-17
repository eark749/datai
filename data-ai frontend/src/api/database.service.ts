import apiClient from './config';

export interface DatabaseConnectionRequest {
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password: string;
  db_schema?: string;
}

export interface DatabaseConnectionResponse {
  id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  db_schema?: string | null;
  is_active: boolean;
  last_tested?: string | null;
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  response_time_ms?: number;
}

export interface ConnectDatabaseResponse {
  connection: DatabaseConnectionResponse;
  schema_loaded: boolean;
  schema_info?: {
    database_type: string;
    table_count: number;
    tables: Array<{
      name: string;
      column_count: number;
    }>;
  };
  error_message?: string;
}

/**
 * Create a new database connection
 */
export const createDatabaseConnection = async (
  data: DatabaseConnectionRequest
): Promise<DatabaseConnectionResponse> => {
  console.log('Creating database connection:', { name: data.name, type: data.db_type });
  const response = await apiClient.post<DatabaseConnectionResponse>('/api/databases', data);
  console.log('Database connection created:', response.data);
  return response.data;
};

/**
 * List all database connections
 */
export const listDatabaseConnections = async (
  skip = 0,
  limit = 50
): Promise<DatabaseConnectionResponse[]> => {
  console.log('Fetching database connections');
  const response = await apiClient.get<DatabaseConnectionResponse[]>('/api/databases', {
    params: { skip, limit },
  });
  console.log('Database connections fetched:', response.data.length);
  return response.data;
};

/**
 * Get a specific database connection
 */
export const getDatabaseConnection = async (
  connectionId: string
): Promise<DatabaseConnectionResponse> => {
  console.log('Fetching database connection:', connectionId);
  const response = await apiClient.get<DatabaseConnectionResponse>(
    `/api/databases/${connectionId}`
  );
  return response.data;
};

/**
 * Update a database connection
 */
export const updateDatabaseConnection = async (
  connectionId: string,
  data: Partial<DatabaseConnectionRequest>
): Promise<DatabaseConnectionResponse> => {
  console.log('Updating database connection:', connectionId);
  const response = await apiClient.put<DatabaseConnectionResponse>(
    `/api/databases/${connectionId}`,
    data
  );
  console.log('Database connection updated');
  return response.data;
};

/**
 * Delete a database connection
 */
export const deleteDatabaseConnection = async (connectionId: string): Promise<void> => {
  console.log('Deleting database connection:', connectionId);
  await apiClient.delete(`/api/databases/${connectionId}`);
  console.log('Database connection deleted');
};

/**
 * Test a database connection
 */
export const testDatabaseConnection = async (
  connectionId: string
): Promise<TestConnectionResponse> => {
  console.log('Testing database connection:', connectionId);
  const response = await apiClient.post<TestConnectionResponse>(
    `/api/databases/${connectionId}/test`
  );
  console.log('Test result:', response.data);
  return response.data;
};

/**
 * Connect to a database and load its schema
 */
export const connectAndLoadSchema = async (
  data: DatabaseConnectionRequest
): Promise<ConnectDatabaseResponse> => {
  console.log('Connecting to database and loading schema:', { name: data.name, type: data.db_type });
  const response = await apiClient.post<ConnectDatabaseResponse>('/api/databases/connect', data);
  console.log('Connection established. Schema loaded:', response.data.schema_loaded);
  if (response.data.schema_info) {
    console.log('Schema info:', {
      database_type: response.data.schema_info.database_type,
      table_count: response.data.schema_info.table_count
    });
  }
  return response.data;
};

