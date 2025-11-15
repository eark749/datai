import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Alert } from './ui/alert';
import { X, Loader2, CheckCircle2 } from 'lucide-react';
import { DatabaseConnection } from './ChatInterface';

interface DatabaseConnectionModalProps {
  onClose: () => void;
  onSave: (connection: Omit<DatabaseConnection, 'id'>) => void;
  existingConnection?: DatabaseConnection | null;
}

export function DatabaseConnectionModal({
  onClose,
  onSave,
  existingConnection,
}: DatabaseConnectionModalProps) {
  const [name, setName] = useState(existingConnection?.name || '');
  const [dbType, setDbType] = useState(existingConnection?.type || 'PostgreSQL');
  const [host, setHost] = useState(existingConnection?.host || '');
  const [port, setPort] = useState(existingConnection?.port || '');
  const [username, setUsername] = useState(existingConnection?.username || '');
  const [password, setPassword] = useState(existingConnection?.password || '');
  const [database, setDatabase] = useState(existingConnection?.database || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [testSuccess, setTestSuccess] = useState(false);

  // Set default port based on DB type
  useEffect(() => {
    if (!existingConnection && !port) {
      const defaultPorts: Record<string, string> = {
        PostgreSQL: '5432',
        MySQL: '3306',
        MongoDB: '27017',
        SQLite: '',
        MariaDB: '3306',
        Oracle: '1521',
        MSSQL: '1433',
      };
      setPort(defaultPorts[dbType] || '');
    }
  }, [dbType, existingConnection, port]);

  const handleTest = async () => {
    setError('');
    setTestSuccess(false);

    if (!name || !host || !username || !database) {
      setError('Please fill in all required fields');
      return;
    }

    if (dbType !== 'SQLite' && !port) {
      setError('Port is required for this database type');
      return;
    }

    setIsLoading(true);

    // Mock test connection
    await new Promise(resolve => setTimeout(resolve, 1500));

    setIsLoading(false);
    setTestSuccess(true);
  };

  const handleSave = () => {
    if (!name || !host || !username || !database) {
      setError('Please fill in all required fields');
      return;
    }

    if (dbType !== 'SQLite' && !port) {
      setError('Port is required for this database type');
      return;
    }

    const connection: Omit<DatabaseConnection, 'id'> = {
      name,
      type: dbType,
      host,
      port,
      username,
      password,
      database,
      connected: testSuccess,
      isDefault: existingConnection?.isDefault || false,
    };

    onSave(connection);
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200">
          <div>
            <h2 className="text-black">
              {existingConnection ? 'Edit Database Connection' : 'Add Database Connection'}
            </h2>
            <p className="text-gray-600">Configure your database settings</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-5">
          <div className="space-y-2">
            <Label htmlFor="name">Connection Name *</Label>
            <Input
              id="name"
              placeholder="My Production DB"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-xl border-slate-200"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="dbType">Database Type *</Label>
            <Select value={dbType} onValueChange={setDbType}>
              <SelectTrigger className="rounded-xl border-slate-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PostgreSQL">PostgreSQL</SelectItem>
                <SelectItem value="MySQL">MySQL</SelectItem>
                <SelectItem value="MongoDB">MongoDB</SelectItem>
                <SelectItem value="SQLite">SQLite</SelectItem>
                <SelectItem value="MariaDB">MariaDB</SelectItem>
                <SelectItem value="Oracle">Oracle</SelectItem>
                <SelectItem value="MSSQL">Microsoft SQL Server</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="host">Host *</Label>
              <Input
                id="host"
                placeholder="localhost"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                className="rounded-xl border-slate-200"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port {dbType !== 'SQLite' && '*'}</Label>
              <Input
                id="port"
                placeholder="5432"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                className="rounded-xl border-slate-200"
                disabled={dbType === 'SQLite'}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="username">Username *</Label>
            <Input
              id="username"
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="rounded-xl border-slate-200"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl border-slate-200"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="database">Database Name *</Label>
            <Input
              id="database"
              placeholder="myapp_db"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              className="rounded-xl border-slate-200"
            />
          </div>

          {error && (
            <Alert className="bg-red-50 border-red-200 text-red-800 rounded-xl">
              {error}
            </Alert>
          )}

          {testSuccess && (
            <Alert className="bg-green-50 border-green-200 text-green-800 rounded-xl flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Connection test successful!
            </Alert>
          )}

          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleTest}
              disabled={isLoading}
              variant="outline"
              className="flex-1 h-11 rounded-xl border-slate-300 hover:bg-slate-100"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                'Test Connection'
              )}
            </Button>
            <Button
              onClick={handleSave}
              disabled={isLoading}
              className="flex-1 h-11 bg-black hover:bg-gray-800 text-white rounded-xl"
            >
              {existingConnection ? 'Update' : 'Save'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
