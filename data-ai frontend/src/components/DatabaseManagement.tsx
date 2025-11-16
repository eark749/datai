import { useState } from 'react';
import { Button } from './ui/button';
import { DatabaseConnection } from './ChatInterface';
import { DatabaseConnectionModal } from './DatabaseConnectionModal';
import { Plus, Database, Trash2, Edit, Star, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { 
  deleteDatabaseConnection as deleteDatabaseConnectionAPI,
  testDatabaseConnection
} from '../api/database.service';
import { AxiosError } from 'axios';

interface DatabaseManagementProps {
  dbConnections: DatabaseConnection[];
  onAddConnection: (connection: Omit<DatabaseConnection, 'id'>) => Promise<void>;
  onUpdateConnection: (id: string, updates: Partial<DatabaseConnection>) => Promise<void>;
  onDeleteConnection: (id: string) => Promise<void>;
  onSetDefaultDb: (id: string) => void;
}

export function DatabaseManagement({
  dbConnections,
  onAddConnection,
  onUpdateConnection,
  onDeleteConnection,
  onSetDefaultDb,
}: DatabaseManagementProps) {
  const [showModal, setShowModal] = useState(false);
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleAddNew = () => {
    setEditingConnection(null);
    setShowModal(true);
  };

  const handleEdit = (connection: DatabaseConnection) => {
    setEditingConnection(connection);
    setShowModal(true);
  };

  const handleSave = async (connection: Omit<DatabaseConnection, 'id'>) => {
    try {
      if (editingConnection) {
        await onUpdateConnection(editingConnection.id, connection);
      } else {
        await onAddConnection(connection);
      }
      setShowModal(false);
      setEditingConnection(null);
    } catch (error) {
      console.error('Error saving connection:', error);
      // Error is handled in the parent component
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this database connection?')) {
      return;
    }
    
    try {
      console.log('DatabaseManagement: Deleting connection:', id);
      await onDeleteConnection(id);
      console.log('DatabaseManagement: Delete successful');
    } catch (error) {
      console.error('DatabaseManagement: Error deleting connection:', error);
      alert('Failed to delete database connection. Please try again.');
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const result = await testDatabaseConnection(id);
      if (result.success) {
        alert(`Connection successful! Response time: ${result.response_time_ms}ms`);
        // Update connection status
        onUpdateConnection(id, { connected: true });
      } else {
        alert(`Connection failed: ${result.message}`);
        onUpdateConnection(id, { connected: false });
      }
    } catch (error) {
      if (error instanceof AxiosError) {
        alert(`Connection test failed: ${error.response?.data?.detail || error.message}`);
      } else {
        alert('Connection test failed. Please check your settings.');
      }
      onUpdateConnection(id, { connected: false });
    } finally {
      setTestingId(null);
    }
  };

  console.log('DatabaseManagement: Rendering with', dbConnections.length, 'connections');

  return (
    <div className="flex flex-col h-full">
      {/* Add Button */}
      <div className="p-3 flex-shrink-0">
        <Button
          onClick={handleAddNew}
          className="w-full bg-black hover:bg-gray-800 text-white rounded-xl shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Database
        </Button>
      </div>

      {/* Connections List - Scrollable */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2" style={{ maxHeight: 'calc(100vh - 250px)' }}>
        {dbConnections.length === 0 ? (
          <div className="text-center py-12 px-4">
            <Database className="h-12 w-12 mx-auto text-slate-300 mb-3" />
            <p className="text-slate-500 mb-2">No databases connected</p>
            <p className="text-xs text-slate-400">Click "Add Database" to get started</p>
          </div>
        ) : (
          <div className="space-y-3 pb-4">
            {dbConnections.map(connection => (
              <div
                key={connection.id}
                className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${
                      connection.connected 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      <Database className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-black flex items-center gap-2">
                        {connection.name}
                        {connection.isDefault && (
                          <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                        )}
                      </h3>
                      <p className="text-xs text-slate-500">{connection.type}</p>
                    </div>
                  </div>

                  <div className="flex gap-1">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEdit(connection)}
                            className="h-8 w-8 p-0 hover:bg-slate-100 rounded-lg"
                          >
                            <Edit className="h-3 w-3" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Edit connection</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(connection.id)}
                            className="h-8 w-8 p-0 hover:bg-red-50 hover:text-red-600 rounded-lg"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Delete connection</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Host:</span>
                    <span className="text-slate-700">{connection.host}:{connection.port}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Database:</span>
                    <span className="text-slate-700">{connection.database}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Status:</span>
                    <span className={`flex items-center gap-1 ${
                      connection.connected ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {connection.connected ? (
                        <>
                          <CheckCircle2 className="h-3 w-3" />
                          Connected
                        </>
                      ) : (
                        <>
                          <XCircle className="h-3 w-3" />
                          Disconnected
                        </>
                      )}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2 mt-3">
                  <Button
                    onClick={() => handleTest(connection.id)}
                    disabled={testingId === connection.id}
                    variant="outline"
                    size="sm"
                    className="flex-1 rounded-lg text-xs border-slate-300 hover:bg-slate-100"
                  >
                    {testingId === connection.id ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Testing...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Test
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => onSetDefaultDb(connection.id)}
                    variant="outline"
                    size="sm"
                    className={`flex-1 rounded-lg text-xs ${
                      connection.isDefault 
                        ? 'bg-yellow-50 border-yellow-400 text-yellow-700 hover:bg-yellow-100' 
                        : 'border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    <Star className={`h-3 w-3 mr-1 ${connection.isDefault ? 'fill-yellow-500 text-yellow-500' : ''}`} />
                    {connection.isDefault ? 'Default' : 'Set Default'}
                  </Button>
                </div>
            </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <DatabaseConnectionModal
          onClose={() => {
            setShowModal(false);
            setEditingConnection(null);
          }}
          onSave={handleSave}
          existingConnection={editingConnection}
        />
      )}
    </div>
  );
}